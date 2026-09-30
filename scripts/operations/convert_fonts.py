#!/usr/bin/env python3
"""Convert all TTF fonts in custom directory to WOFF2 format"""

import os
from pathlib import Path
from fontTools.ttLib import TTFont

def convert_ttf_to_woff2(ttf_path, woff2_path):
    """Convert a TTF file to WOFF2 format"""
    try:
        font = TTFont(ttf_path)
        font.flavor = "woff2"
        font.save(woff2_path)
        font.close()
        print(f"✓ Converted: {ttf_path.name} -> {woff2_path.name}")
        return True
    except Exception as e:
        print(f"✗ Failed to convert {ttf_path.name}: {e}")
        return False

def main():
    custom_fonts_dir = Path("/home/zayne/projects/pwaninet/static/fonts/custom")
    
    if not custom_fonts_dir.exists():
        print(f"Directory not found: {custom_fonts_dir}")
        return
    
    ttf_files = list(custom_fonts_dir.glob("*.ttf"))
    
    if not ttf_files:
        print("No TTF files found in the custom fonts directory")
        return
    
    print(f"Found {len(ttf_files)} TTF files to convert...")
    print("-" * 50)
    
    converted = 0
    failed = 0
    
    for ttf_file in ttf_files:
        woff2_file = ttf_file.with_suffix('.woff2')
        
        # Skip if WOFF2 already exists and is newer
        if woff2_file.exists() and woff2_file.stat().st_mtime > ttf_file.stat().st_mtime:
            print(f"⊘ Skipping (already converted): {ttf_file.name}")
            continue
        
        if convert_ttf_to_woff2(ttf_file, woff2_file):
            converted += 1
        else:
            failed += 1
    
    print("-" * 50)
    print(f"Conversion complete: {converted} converted, {failed} failed")
    
    # Show size comparison
    print("\nSize comparison:")
    print("-" * 50)
    for ttf_file in sorted(ttf_files):
        woff2_file = ttf_file.with_suffix('.woff2')
        if woff2_file.exists():
            ttf_size = ttf_file.stat().st_size / 1024  # KB
            woff2_size = woff2_file.stat().st_size / 1024  # KB
            savings = ((ttf_size - woff2_size) / ttf_size) * 100
            print(f"{ttf_file.name:40} {ttf_size:8.1f} KB -> {woff2_file.name:40} {woff2_size:8.1f} KB ({savings:5.1f}% smaller)")

if __name__ == "__main__":
    main()
