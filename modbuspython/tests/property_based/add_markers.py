"""Script to add pytest markers to property-based test files.

This script adds @pytest.mark.property and feature-specific markers
to all test functions in the property_based directory.
"""

import re
from pathlib import Path


def add_markers_to_file(file_path: Path, feature_marker: str):
    """Add pytest markers to all test functions in a file."""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    modified = False
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        new_lines.append(line)

        # Check if this is a @settings line
        if line.strip().startswith("@settings("):
            # Check if next line is a test function definition
            if i + 1 < len(lines) and lines[i + 1].strip().startswith("def test_"):
                # Check if markers are already present
                has_property_marker = False
                has_feature_marker = False

                # Look back to see if markers exist
                for j in range(max(0, i - 5), i + 1):
                    if "@pytest.mark.property" in lines[j]:
                        has_property_marker = True
                    if f"@pytest.mark.{feature_marker}" in lines[j]:
                        has_feature_marker = True

                # Add markers if not present
                if not has_property_marker:
                    new_lines.append("@pytest.mark.property\n")
                    modified = True
                if not has_feature_marker:
                    new_lines.append(f"@pytest.mark.{feature_marker}\n")
                    modified = True

        i += 1

    # Write back if changes were made
    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return True
    return False


def main():
    """Add markers to all property-based test files."""
    test_dir = Path(__file__).parent

    # Map files to their feature markers
    file_markers = {
        "test_validation_properties.py": "validation",
        "test_config_properties.py": "config",
        "test_retry_properties.py": "retry",
        "test_error_resilience_properties.py": "error_resilience",
        "test_resource_cleanup_properties.py": "resource_cleanup",
        "test_config_validation_properties.py": "config_validation",
        "test_database_properties.py": "database",
        "test_migration_properties.py": "migration",
    }

    for filename, marker in file_markers.items():
        file_path = test_dir / filename
        if file_path.exists():
            if add_markers_to_file(file_path, marker):
                print(f"✓ Added markers to {filename}")
            else:
                print(f"- No changes needed for {filename}")
        else:
            print(f"✗ File not found: {filename}")


if __name__ == "__main__":
    main()
