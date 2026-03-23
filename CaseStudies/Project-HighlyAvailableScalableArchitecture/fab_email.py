"""
Pattern Phrase Generator
Generates all possible phrase combinations from pattern syntax for testing DLP/content detection rules
 
Pattern Syntax:
- {option1|option2} = Alternation (choose one)
- {%any%[,N]} = Wildcard (0 to N words, generates 0 and 1-word variations only)
- Nested braces = {word|{multi word}} supported
 
Example:
feature_one: {car|bicycle}
feature_two: {drove|{used my}} {%any%[,2]} {yesterday|{a few minutes ago}}
Rule: feature_one AND feature_two
"""
 
import openpyxl
from openpyxl import Workbook
import re
from itertools import product
 
 
# ==================== CONFIGURATION SECTION ====================
 
# Define features as pattern strings
FEATURES = {
    "feature_one": "{car|bicycle}",
    "feature_two": "{drove|{used my}} {%any%[,2]} {yesterday|{a few minutes ago}}"
}
 
# Define the rule (currently supports AND only)
RULE = "feature_one AND feature_two"
 
# Wildcard word pool for {%any%[,N]} replacement
# Add your language-specific words here
WILDCARD_WORDS = [
    "myself",
    "own",
    "nonetheless",
    "red bandana",
    "quickly",
    "very",
    "really",
    "absolutely",
    "completely",
]
 
# Output filename
OUTPUT_FILENAME = "generated_phrases.xlsx"
 
# ==================== END CONFIGURATION ====================
 
 
def extract_alternations(pattern):
    """
    Extract all {option1|option2|...} patterns from a string
    Returns list of tuples: (full_match, options_list, start_pos, end_pos)
    Handles nested braces
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
    Example: "car|{used my}|bike" -> ["car", "{used my}", "bike"]
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
    """Check if text is a wildcard pattern like {%any%[,2]}"""
    return bool(re.match(r'\{%any%\[\s*,\s*(\d+)\s*\]\}', text))
 
 
def get_wildcard_max(text):
    """Extract max number from wildcard pattern {%any%[,N]}"""
    match = re.match(r'\{%any%\[\s*,\s*(\d+)\s*\]\}', text)
    if match:
        return int(match.group(1))
    return 0
 
 
def generate_wildcard_variations(max_words, word_pool):
    """
    Generate wildcard variations (0 words and 1 word only)
    Returns list of strings
    """
    variations = [""]  # 0 words (empty string)
    
    # Add 1-word variations
    for word in word_pool:
        variations.append(word)
    
    return variations
 
 
def expand_pattern(pattern, word_pool):
    """
    Expand a pattern into all possible variations
    Returns list of strings
    """
    # Base case: no alternations
    alternations = extract_alternations(pattern)
    
    if not alternations:
        return [pattern]
    
    # Process first alternation
    full_match, options, start, end = alternations[0]
    
    # Check if this is a wildcard
    if is_wildcard(full_match):
        max_words = get_wildcard_max(full_match)
        replacements = generate_wildcard_variations(max_words, word_pool)
    else:
        # Recursively expand each option
        replacements = []
        for option in options:
            # Remove outer braces if present and expand
            option = option.strip()
            if option.startswith('{') and option.endswith('}'):
                option = option[1:-1]
            expanded = expand_pattern(option, word_pool)
            replacements.extend(expanded)
    
    # Generate all variations
    results = []
    for replacement in replacements:
        # Replace the alternation with each option
        new_pattern = pattern[:start] + replacement + pattern[end:]
        # Recursively expand remaining alternations
        expanded = expand_pattern(new_pattern, word_pool)
        results.extend(expanded)
    
    return results
 
 
def clean_phrase(phrase):
    """Clean up extra spaces in generated phrase"""
    # Replace multiple spaces with single space
    phrase = re.sub(r'\s+', ' ', phrase)
    return phrase.strip()
 
 
def generate_feature_variations(feature_pattern, word_pool):
    """
    Generate all variations for a single feature
    Returns list of cleaned phrases
    """
    variations = expand_pattern(feature_pattern, word_pool)
    return [clean_phrase(v) for v in variations]
 
 
def combine_features_and(feature_variations_dict):
    """
    Combine multiple features using AND logic (concatenation)
    feature_variations_dict: {feature_name: [variation1, variation2, ...]}
    Returns list of combined phrases
    """
    # Get all feature names in order
    feature_names = list(feature_variations_dict.keys())
    
    # Get all variations for each feature
    variations_lists = [feature_variations_dict[name] for name in feature_names]
    
    # Generate all combinations
    combined = []
    for combo in product(*variations_lists):
        # Concatenate with spaces
        phrase = ' '.join(combo)
        combined.append(clean_phrase(phrase))
    
    return combined
 
 
def parse_rule_and_generate(rule, features, word_pool):
    """
    Parse rule and generate all phrase combinations
    Currently supports AND only
    """
    # Extract feature names from rule
    feature_names = re.findall(r'feature_\w+', rule)
    
    # Generate variations for each feature
    feature_variations = {}
    for feature_name in feature_names:
        if feature_name in features:
            variations = generate_feature_variations(features[feature_name], word_pool)
            feature_variations[feature_name] = variations
            print(f"  {feature_name}: {len(variations)} variations")
    
    # Combine features based on rule
    if 'AND' in rule:
        combined = combine_features_and(feature_variations)
    else:
        # For now, just concatenate all variations
        combined = []
        for variations in feature_variations.values():
            combined.extend(variations)
    
    return combined
 
 
def write_phrases_to_excel(phrases, filename):
    """
    Write phrases to Excel file (one column, one phrase per row)
    """
    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Generated Phrases"
    
    # Write header
    ws.append(["Phrase"])
    
    # Write phrases
    for phrase in phrases:
        ws.append([phrase])
    
    # Save
    wb.save(filename)
    print(f"\n✓ Excel file created: {filename}")
    print(f"✓ Total phrases generated: {len(phrases)}")
 
 
def main():
    """Main execution function"""
    print("=" * 60)
    print("Pattern Phrase Generator")
    print("=" * 60)
    
    print(f"\nConfiguration:")
    print(f"  Features defined: {len(FEATURES)}")
    for name, pattern in FEATURES.items():
        print(f"    {name}: {pattern}")
    print(f"  Rule: {RULE}")
    print(f"  Wildcard words: {len(WILDCARD_WORDS)}")
    print(f"  Output file: {OUTPUT_FILENAME}")
    
    print("\nGenerating variations...")
    
    # Generate all phrases
    phrases = parse_rule_and_generate(RULE, FEATURES, WILDCARD_WORDS)
    
    # Write to Excel
    write_phrases_to_excel(phrases, OUTPUT_FILENAME)
    
    print("\n" + "=" * 60)
    print("Generation Complete!")
    print("=" * 60)
    
    # Show first 10 examples
    print("\nFirst 10 generated phrases:")
    for i, phrase in enumerate(phrases[:10], 1):
        print(f"  {i}. {phrase}")
    
    if len(phrases) > 10:
        print(f"  ... and {len(phrases) - 10} more")
