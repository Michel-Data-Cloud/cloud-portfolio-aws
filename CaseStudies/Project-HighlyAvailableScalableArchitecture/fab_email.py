"""
Enhanced Pattern Phrase Generator
Generates all possible phrase combinations from complex pattern syntax for DLP/content detection testing
 
Pattern Syntax:
- {option1|option2} = Alternation (choose one)
- {%any%[,N]} = Wildcard (generates ALL variations from 0 to N words)
- Nested braces = {{one|two} join}|{join {one|two}} supported
- Top-level pipes = {option1}|{option2} supported
 
Two-Feature Structure:
- feature_one: Usually simple alternation like {car|bicycle} or {fix|fixes}
- feature_two: More complex patterns with nesting and wildcards
- Rule: Almost always "feature_one AND feature_two"
- If feature_one is empty (""), only feature_two is used
 
Example:
feature_one: {fix|fixes}
feature_two: {{one|two|three} join}|{join {one|two|three}}
Rule: feature_one AND feature_two
Output: fix one join, fix two join, ..., fixes join three (12 total)
"""
 
import openpyxl
from openpyxl import Workbook
import re
from itertools import product
 
 
# ==================== CONFIGURATION SECTION ====================
# Modify these values before running the script
 
# Define features as pattern strings
# feature_one: Usually simple alternation, can be empty "" if not needed
# feature_two: Can be complex with nesting, wildcards, top-level pipes
FEATURES = {
    "feature_one": "{fix|fixes}",
    "feature_two": "{{one|two|three} join}|{join {one|two|three}}"
}
 
# Define the rule (almost always "feature_one AND feature_two")
RULE = "feature_one AND feature_two"
 
# Wildcard word pool for {%any%[,N]} replacement
# Define words and phrases of different lengths
# The generator will use phrases with word count <= N for {%any%[,N]}
WILDCARD_WORDS = [
    # 1-word entries
    "in",
    "for",
    "more",
    "very",
    "quickly",
    "own",
    "myself",
    "nonetheless",
    
    # 2-word entries (for {%any%[,2]} and higher)
    "in for",
    "for more",
    "very quickly",
    "red bandana",
    
    # 3-word entries (for {%any%[,3]} and higher)
    "in for more",
    "very quickly indeed",
]
 
# Output filename
OUTPUT_FILENAME = "generated_phrases.xlsx"
 
# ==================== END CONFIGURATION ====================
 
 
def count_words(text):
    """
    Count the number of words in a text string
    
    Args:
        text: String to count words in
        
    Returns:
        Integer count of words (0 if empty string)
        
    Example:
        count_words("hello world") -> 2
        count_words("") -> 0
    """
    return len(text.split()) if text else 0
 
 
def split_by_top_level_pipe(pattern):
    """
    Split pattern by top-level pipes (pipes outside all braces)
    This handles patterns like "{one join}|{join one}" 
    
    Args:
        pattern: String pattern to split
        
    Returns:
        List of options if top-level pipes found, None otherwise
        
    Example:
        "{one join}|{join one}" -> ["{one join}", "{join one}"]
        "{one|two} join" -> None (pipe is inside braces)
    """
    options = []
    current = ""
    brace_count = 0
    
    for char in pattern:
        if char == '{':
            brace_count += 1
            current += char
        elif char == '}':
            brace_count -= 1
            current += char
        elif char == '|' and brace_count == 0:
            # Top-level pipe found (outside all braces)
            if current:
                options.append(current)
            current = ""
        else:
            current += char
    
    if current:
        options.append(current)
    
    # If no top-level pipes found, return None
    return options if len(options) > 1 else None
 
 
def extract_alternations(pattern):
    """
    Extract all {option1|option2|...} patterns from a string
    Handles nested braces properly
    
    Args:
        pattern: String pattern to extract from
        
    Returns:
        List of tuples: (full_match, options_list, start_pos, end_pos)
        
    Example:
        "{car|bicycle} drove" -> [("{car|bicycle}", ["car", "bicycle"], 0, 13)]
    """
    alternations = []
    i = 0
    
    while i < len(pattern):
        if pattern[i] == '{':
            # Find matching closing brace (handle nesting)
            brace_count = 1
            j = i + 1
            
            while j < len(pattern) and brace_count > 0:
                if pattern[j] == '{':
                    brace_count += 1
                elif pattern[j] == '}':
                    brace_count -= 1
                j += 1
            
            if brace_count == 0:
                # Found complete alternation
                content = pattern[i+1:j-1]
                
                # Split by | but respect nested braces
                options = split_by_pipe(content)
                alternations.append((pattern[i:j], options, i, j))
            
            i = j
        else:
            i += 1
    
    return alternations
 
 
def split_by_pipe(content):
    """
    Split content by | but respect nested braces
    This ensures {used my} stays together when splitting
    
    Args:
        content: String to split (content inside braces)
        
    Returns:
        List of options
        
    Example:
        "car|{used my}|bike" -> ["car", "{used my}", "bike"]
    """
    options = []
    current = ""
    brace_count = 0
    
    for char in content:
        if char == '{':
            brace_count += 1
            current += char
        elif char == '}':
            brace_count -= 1
            current += char
        elif char == '|' and brace_count == 0:
            options.append(current)
            current = ""
        else:
            current += char
    
    if current:
        options.append(current)
    
    return options
 
 
def is_wildcard(text):
    """
    Check if text is a wildcard pattern like {%any%[,2]}
    
    Args:
        text: String to check
        
    Returns:
        Boolean - True if wildcard pattern, False otherwise
        
    Example:
        is_wildcard("{%any%[,2]}") -> True
        is_wildcard("{car|bike}") -> False
    """
    return bool(re.match(r'\{%any%\[\s*,\s*(\d+)\s*\]\}', text))
 
 
def get_wildcard_max(text):
    """
    Extract max number from wildcard pattern {%any%[,N]}
    
    Args:
        text: Wildcard pattern string
        
    Returns:
        Integer N value, or 0 if not a valid wildcard
        
    Example:
        get_wildcard_max("{%any%[,3]}") -> 3
    """
    match = re.match(r'\{%any%\[\s*,\s*(\d+)\s*\]\}', text)
    if match:
        return int(match.group(1))
    return 0
 
 
def generate_wildcard_variations(max_words, word_pool):
    """
    Generate wildcard variations from 0 to max_words
    Uses phrases from word_pool that have word count <= max_words
    
    Args:
        max_words: Maximum number of words (N from {%any%[,N]})
        word_pool: List of words/phrases to use
        
    Returns:
        List of strings (includes empty string for 0 words)
        
    Example:
        For max_words=2 and pool=["in", "for", "in for", "in for more"]:
        Returns: ["", "in", "for", "in for"]
        (excludes "in for more" because it has 3 words)
    """
    variations = [""]  # 0 words (empty string)
    
    # Add all phrases from pool that have <= max_words
    for phrase in word_pool:
        word_count = count_words(phrase)
        if word_count > 0 and word_count <= max_words:
            variations.append(phrase)
    
    return variations
 
 
def expand_pattern(pattern, word_pool):
    """
    Recursively expand a pattern into all possible variations
    Handles top-level pipes, nested braces, and wildcards
    
    Args:
        pattern: String pattern to expand
        word_pool: List of words/phrases for wildcard replacement
        
    Returns:
        List of all possible expanded strings
        
    Example:
        expand_pattern("{car|bike} drove", []) -> ["car drove", "bike drove"]
        
    Processing order:
    1. Check for top-level pipes (outside all braces)
    2. Check for brace alternations {option1|option2}
    3. Check for wildcards {%any%[,N]}
    4. Recursively expand until no more patterns remain
    """
    pattern = pattern.strip()
    
    # First, check for top-level pipes (outside all braces)
    # Example: "{one join}|{join one}" should split into two separate expansions
    top_level_options = split_by_top_level_pipe(pattern)
    if top_level_options:
        # Expand each top-level option separately
        all_results = []
        for option in top_level_options:
            expanded = expand_pattern(option, word_pool)
            all_results.extend(expanded)
        return all_results
    
    # No top-level pipes, look for brace alternations
    alternations = extract_alternations(pattern)
    
    if not alternations:
        # Base case: no more patterns to expand
        return [pattern]
    
    # Process first alternation found
    full_match, options, start, end = alternations[0]
    
    # Check if this is a wildcard pattern
    if is_wildcard(full_match):
        max_words = get_wildcard_max(full_match)
        replacements = generate_wildcard_variations(max_words, word_pool)
    else:
        # Regular alternation - recursively expand each option
        replacements = []
        for option in options:
            # Remove outer braces if present and expand
            option = option.strip()
            if option.startswith('{') and option.endswith('}'):
                option = option[1:-1]
            expanded = expand_pattern(option, word_pool)
            replacements.extend(expanded)
    
    # Generate all variations by replacing the first alternation with each replacement
    results = []
    for replacement in replacements:
        # Replace the alternation with the current replacement
        new_pattern = pattern[:start] + replacement + pattern[end:]
        # Recursively expand remaining alternations in the new pattern
        expanded = expand_pattern(new_pattern, word_pool)
        results.extend(expanded)
    
    return results
 
 
def clean_phrase(phrase):
    """
    Clean up extra spaces in generated phrase
    Multiple consecutive spaces become single space
    
    Args:
        phrase: String to clean
        
    Returns:
        Cleaned string with single spaces and trimmed ends
        
    Example:
        clean_phrase("car  drove   yesterday") -> "car drove yesterday"
    """
    # Replace multiple spaces with single space
    phrase = re.sub(r'\s+', ' ', phrase)
    return phrase.strip()
 
 
def generate_feature_variations(feature_pattern, word_pool):
    """
    Generate all variations for a single feature
    
    Args:
        feature_pattern: Pattern string for the feature
        word_pool: List of words/phrases for wildcards
        
    Returns:
        List of unique cleaned phrases
        
    Example:
        feature_pattern = "{car|bike}"
        Returns: ["car", "bike"]
    """
    variations = expand_pattern(feature_pattern, word_pool)
    cleaned = [clean_phrase(v) for v in variations]
    
    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for phrase in cleaned:
        if phrase not in seen:
            seen.add(phrase)
            unique.append(phrase)
    
    return unique
 
 
def combine_features_and(feature_variations_dict):
    """
    Combine multiple features using AND logic (concatenation with space)
    Skips features that have empty variations
    
    Args:
        feature_variations_dict: Dictionary {feature_name: [variation1, variation2, ...]}
        
    Returns:
        List of combined phrases
        
    Example:
        {
            "feature_one": ["car", "bike"],
            "feature_two": ["drove", "used"]
        }
        Returns: ["car drove", "car used", "bike drove", "bike used"]
        
    If feature_one is empty:
        {
            "feature_one": [""],
            "feature_two": ["drove", "used"]
        }
        Returns: ["drove", "used"]
    """
    # Get all feature names in order
    feature_names = list(feature_variations_dict.keys())
    
    # Filter out features that only have empty string
    active_features = {}
    for name in feature_names:
        variations = feature_variations_dict[name]
        # Only include if not just [""]
        if variations and not (len(variations) == 1 and variations[0] == ""):
            active_features[name] = variations
    
    # If no active features, return empty list
    if not active_features:
        return []
    
    # Get all variations for each active feature
    active_names = list(active_features.keys())
    variations_lists = [active_features[name] for name in active_names]
    
    # Generate all combinations using Cartesian product
    combined = []
    for combo in product(*variations_lists):
        # Concatenate with spaces
        phrase = ' '.join(combo)
        combined.append(clean_phrase(phrase))
    
    return combined
 
 
def parse_rule_and_generate(rule, features, word_pool):
    """
    Parse rule and generate all phrase combinations
    Currently supports AND logic only
    
    Args:
        rule: String rule like "feature_one AND feature_two"
        features: Dictionary of feature patterns
        word_pool: List of words/phrases for wildcards
        
    Returns:
        List of all generated phrases
        
    Process:
    1. Extract feature names from rule
    2. Generate variations for each feature
    3. Combine features based on rule logic (AND)
    4. Return all combinations
    """
    # Extract feature names from rule (e.g., "feature_one", "feature_two")
    feature_names = re.findall(r'feature_\w+', rule)
    
    # Generate variations for each feature
    feature_variations = {}
    for feature_name in feature_names:
        if feature_name in features:
            print(f"\nProcessing {feature_name}...")
            print(f"  Pattern: {features[feature_name]}")
            
            # Handle empty feature
            if features[feature_name] == "":
                variations = [""]
                print(f"  Empty feature - skipping")
            else:
                variations = generate_feature_variations(features[feature_name], word_pool)
                print(f"  Generated: {len(variations)} variations")
                
                # Show first few examples
                print(f"  Examples:")
                for i, var in enumerate(variations[:5], 1):
                    print(f"    {i}. {var}")
                if len(variations) > 5:
                    print(f"    ... and {len(variations) - 5} more")
            
            feature_variations[feature_name] = variations
    
    # Combine features based on rule
    if 'AND' in rule:
        combined = combine_features_and(feature_variations)
    else:
        # Single feature or just concatenate all variations
        combined = []
        for variations in feature_variations.values():
            combined.extend(variations)
    
    return combined
 
 
def write_phrases_to_excel(phrases, filename):
    """
    Write phrases to Excel file (one column, one phrase per row)
    
    Args:
        phrases: List of phrase strings
        filename: Output Excel filename
        
    Creates:
        Excel file with header "Phrase" and one phrase per row
    """
    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Generated Phrases"
    
    # Write header
    ws.append(["Phrase"])
    
    # Write phrases (one per row)
    for phrase in phrases:
        ws.append([phrase])
    
    # Save
    wb.save(filename)
    print(f"\n✓ Excel file created: {filename}")
    print(f"✓ Total phrases generated: {len(phrases)}")
 
 
def main():
    """
    Main execution function
    
    Process:
    1. Display configuration
    2. Generate variations for each feature
    3. Combine features based on rule
    4. Write results to Excel
    5. Display summary and examples
    """
    print("=" * 70)
    print("Enhanced Pattern Phrase Generator")
    print("=" * 70)
    
    print(f"\nConfiguration:")
    print(f"  Features defined: {len(FEATURES)}")
    for name, pattern in FEATURES.items():
        display_pattern = '""' if pattern == "" else pattern
        print(f"    {name}: {display_pattern}")
    print(f"  Rule: {RULE}")
    print(f"  Wildcard pool entries: {len(WILDCARD_WORDS)}")
    print(f"  Output file: {OUTPUT_FILENAME}")
    
    print("\n" + "=" * 70)
    print("Generating variations...")
    print("=" * 70)
    
    # Generate all phrases
    phrases = parse_rule_and_generate(RULE, FEATURES, WILDCARD_WORDS)
    
    # Write to Excel
    write_phrases_to_excel(phrases, OUTPUT_FILENAME)
    
    print("\n" + "=" * 70)
    print("Generation Complete!")
    print("=" * 70)
    
    # Show all phrases if not too many
    if len(phrases) <= 20:
        print(f"\nAll {len(phrases)} generated phrases:")
        for i, phrase in enumerate(phrases, 1):
            print(f"  {i}. {phrase}")
    else:
        print(f"\nFirst 10 generated phrases:")
        for i, phrase in enumerate(phrases[:10], 1):
            print(f"  {i}. {phrase}")
        print(f"  ... and {len(phrases) - 10} more")
 
 
if __name__ == "__main__":
    main()
 
