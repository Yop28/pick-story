#!/usr/bin/env python3
import json
import os
import re
import sys
import glob
import copy

# Map 1-based global index to 0-based scene index and 0-based local shot index
def map_global_to_local(global_idx, shot_counts):
    current = 0
    for scene_idx, count in enumerate(shot_counts):
        if current < global_idx <= current + count:
            local_idx = global_idx - current - 1
            return scene_idx, local_idx
        current += count
    raise IndexError(f"Global index {global_idx} is out of bounds for shot counts {shot_counts}")

def main():
    pick_file = "pick.txt"
    template_preset = "preset-3.json"
    
    if not os.path.exists(pick_file):
        print(f"Error: {pick_file} not found.", file=sys.stderr)
        sys.exit(1)
        
    if not os.path.exists(template_preset):
        print(f"Error: Template preset file '{template_preset}' not found.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Loading template preset '{template_preset}'...")
    with open(template_preset, 'r', encoding='utf-8') as f:
        template_data = json.load(f)
        
    # Calculate template shot counts per scene
    template_scenes = template_data.get("storyboard", [])
    template_shot_counts = [len(s.get("shots", [])) for s in template_scenes]
    total_template_shots = sum(template_shot_counts)
    print(f"Template '{template_preset}' has {len(template_scenes)} scenes, shot counts: {template_shot_counts} (Total: {total_template_shots})")
    
    # Parse pick.txt
    # Format of each line: m:preset_num-source_global_idx
    # e.g., 1:2-1
    pick_mappings = []
    # Match "A:B-C" pattern; any trailing text (e.g. Korean comments in parentheses) is ignored
    line_regex = re.compile(r"^\s*(\d+)\s*:\s*(\d+)\s*-\s*(\d+)\b")
    
    with open(pick_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            match = line_regex.match(line_str)
            if not match:
                print(f"Warning: Line {line_num} in '{pick_file}' is in invalid format and will be skipped: '{line_str}'", file=sys.stderr)
                continue
            target_global_idx = int(match.group(1))
            preset_num = int(match.group(2))
            source_global_idx = int(match.group(3))
            pick_mappings.append((target_global_idx, preset_num, source_global_idx))
            
    if not pick_mappings:
        print(f"Error: No valid shot picking rules found in '{pick_file}'.", file=sys.stderr)
        sys.exit(1)
        
    # Sort mappings by target global index
    pick_mappings.sort(key=lambda x: x[0])
    print(f"Parsed {len(pick_mappings)} pick rules from '{pick_file}':")
    for t_idx, p_num, s_idx in pick_mappings:
        print(f"  Target Global Shot {t_idx} <- preset-{p_num}.json's Global Shot {s_idx}")
        
    # Load required presets and cache their shot counts
    presets_cache = {}
    def load_preset(preset_num):
        if preset_num in presets_cache:
            return presets_cache[preset_num]
        
        filename = f"preset-{preset_num}.json"
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Preset file '{filename}' does not exist.")
            
        with open(filename, 'r', encoding='utf-8') as pf:
            p_data = json.load(pf)
            
        p_scenes = p_data.get("storyboard", [])
        p_shot_counts = [len(ps.get("shots", [])) for ps in p_scenes]
        presets_cache[preset_num] = (p_data, p_shot_counts)
        return presets_cache[preset_num]

    # Reconstruct the shots inside target storyboard scenes
    # Option 2 chosen: only reconstruct with specified shots
    # Clear the shots array of each scene in template
    for s in template_scenes:
        s["shots"] = []
        
    for target_global_idx, preset_num, source_global_idx in pick_mappings:
        try:
            # Map target_global_idx to template scene to know where to insert it
            target_scene_idx, _ = map_global_to_local(target_global_idx, template_shot_counts)
        except IndexError as e:
            print(f"Error mapping target global shot {target_global_idx}: {e}", file=sys.stderr)
            sys.exit(1)
            
        try:
            # Load source preset
            source_data, source_shot_counts = load_preset(preset_num)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
            
        try:
            # Map source_global_idx to source scene and local shot index
            source_scene_idx, source_local_idx = map_global_to_local(source_global_idx, source_shot_counts)
        except IndexError as e:
            print(f"Error mapping source global shot {source_global_idx} in preset-{preset_num}.json: {e}", file=sys.stderr)
            sys.exit(1)
            
        # Extract the shot object
        try:
            src_shot = source_data["storyboard"][source_scene_idx]["shots"][source_local_idx]
        except IndexError:
            print(f"Error: Could not retrieve shot index {source_local_idx} in scene {source_scene_idx} of preset-{preset_num}.json", file=sys.stderr)
            sys.exit(1)
            
        # Deep-copy the source shot, then overwrite shotNumber with the target global index (A)
        copied_shot = copy.deepcopy(src_shot)
        copied_shot["shotNumber"] = target_global_idx  # A값 그대로 (shotId는 소스 원본 유지)
        
        # Append the copied shot to the target scene
        template_scenes[target_scene_idx]["shots"].append(copied_shot)
        
    # Write the output file using the next available version number
    # Option 3 chosen: auto-increment version number based on existing files
    files = glob.glob("all-*.json")
    max_ver = 0
    for f in files:
        basename = os.path.basename(f)
        match = re.match(r"^all-(\d+)\.json$", basename)
        if match:
            ver = int(match.group(1))
            if ver > max_ver:
                max_ver = ver
    next_ver = max_ver + 1
    output_filename = f"all-{next_ver}.json"
    
    print(f"Writing reconstructed storyboard to '{output_filename}'...")
    with open(output_filename, 'w', encoding='utf-8') as out_f:
        json.dump(template_data, out_f, indent=2, ensure_ascii=False)
        
    print(f"Successfully generated '{output_filename}'!")

if __name__ == "__main__":
    main()
