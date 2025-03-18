import os
import re
from collections import defaultdict
from difflib import SequenceMatcher
import inflect

# Initialize the inflect engine for handling singular/plural
p = inflect.engine()

def normalize_hashtag(tag):
    # Remove # and convert to lowercase
    tag = tag.lower().strip('#')
    # Remove special characters and spaces
    tag = re.sub(r'[^a-z0-9/]', '', tag)
    return tag

def is_similar(str1, str2, threshold=0.85):
    # Use SequenceMatcher to determine string similarity
    similarity = SequenceMatcher(None, str1, str2).ratio()
    return similarity > threshold

def are_singular_plural_pairs(word1, word2):
    # Check if words are singular/plural pairs
    if p.singular_noun(word1) and p.singular_noun(word1) == word2:
        return True
    if p.singular_noun(word2) and p.singular_noun(word2) == word1:
        return True
    # Check if one is the singular of the other
    if word1 == p.singular_noun(word2) or word2 == p.singular_noun(word1):
        return True
    return False

def find_hashtags(content):
    # Find all hashtags in the content, including those in YAML frontmatter
    hashtags = re.findall(r'#[\w/]+', content)
    # Also find hashtags in YAML list format (- "#tag")
    yaml_tags = re.findall(r'[\n\r]\s*-\s*"#([^"]+)"', content)
    hashtags.extend(['#' + tag for tag in yaml_tags])
    return list(set(hashtags))

def group_similar_tags(tags):
    # Dictionary to store groups of similar tags
    groups = defaultdict(set)
    processed = set()

    # First pass: group exact matches after normalization
    normalized_map = defaultdict(set)
    for tag in tags:
        norm = normalize_hashtag(tag)
        normalized_map[norm].add(tag)

    # Second pass: check for singular/plural relationships and similarity
    normalized_tags = list(normalized_map.keys())
    for i, norm1 in enumerate(normalized_tags):
        if norm1 in processed:
            continue
            
        current_group = normalized_map[norm1]
        
        for j in range(i + 1, len(normalized_tags)):
            norm2 = normalized_tags[j]
            if norm2 in processed:
                continue
                
            # Check for singular/plural relationship or similarity
            if are_singular_plural_pairs(norm1, norm2) or is_similar(norm1, norm2):
                current_group.update(normalized_map[norm2])
                processed.add(norm2)
        
        # Use the shortest normalized form as the canonical version
        canonical = min(current_group, key=len)
        groups[canonical].update(current_group)
        processed.add(norm1)

    return groups

def suggest_nested_tags(tags):
    # Define common parent categories
    categories = {
        'tech': ['event', 'conference', 'expo', 'meetup'],
        'workspace': ['automation', 'innovation', 'management'],
        'ai': ['interface', 'automation', 'control'],
        'smart': ['building', 'workplace', 'office', 'meeting']
    }
    
    nested_tags = {}
    for tag in tags:
        norm_tag = normalize_hashtag(tag)
        for category, subtypes in categories.items():
            for subtype in subtypes:
                if subtype in norm_tag and category in norm_tag:
                    nested_tag = f"#{category}/{subtype}"
                    nested_tags[tag] = nested_tag
                    break
    return nested_tags

def process_markdown_files(content_dir):
    all_tags = set()
    file_tags = defaultdict(set)
    
    # First pass: collect all hashtags
    for root, _, files in os.walk(content_dir):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        tags = find_hashtags(content)
                        all_tags.update(tags)
                        file_tags[file_path].update(tags)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
    
    # Group similar tags
    tag_groups = group_similar_tags(all_tags)
    
    # Suggest nested tags
    nested_tags = suggest_nested_tags(all_tags)
    
    return tag_groups, nested_tags, file_tags

def update_files(content_dir, tag_groups, nested_tags, file_tags):
    # Create mappings for replacement
    replacements = {}
    for canonical, group in tag_groups.items():
        for tag in group:
            if tag in nested_tags:
                replacements[tag] = nested_tags[tag]
            else:
                replacements[tag] = canonical

    # Update files
    for file_path, tags in file_tags.items():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            new_content = content
            for old_tag, new_tag in replacements.items():
                # Replace in regular content
                new_content = new_content.replace(old_tag, new_tag)
                # Replace in YAML frontmatter
                new_content = new_content.replace(f'- "{old_tag}"', f'- "{new_tag}"')

            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {file_path}")
        except Exception as e:
            print(f"Error updating {file_path}: {e}")

    return replacements

def main():
    content_dir = 'content'
    
    print("Processing files...")
    tag_groups, nested_tags, file_tags = process_markdown_files(content_dir)
    
    print("\nHashtag Mapping Report:")
    print("=====================")
    
    print("\nTag Groups:")
    for canonical, group in sorted(tag_groups.items()):
        print(f"\nCanonical: {canonical}")
        others = group - {canonical}
        if others:
            print("Variants:", ", ".join(sorted(others)))
    
    print("\nNested Tags:")
    for original, nested in sorted(nested_tags.items()):
        print(f"{original} -> {nested}")
    
    print("\nUpdating files...")
    replacements = update_files(content_dir, tag_groups, nested_tags, file_tags)
    
    print("\nSummary of Changes:")
    print("=================")
    for old_tag, new_tag in sorted(replacements.items()):
        if old_tag != new_tag:
            print(f"{old_tag} -> {new_tag}")
    
    print("\nDone!")

if __name__ == "__main__":
    main() 