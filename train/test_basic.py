"""
Quick test for Buddy Train functionality
"""

import os
import tempfile
from pathlib import Path


def test_data_processor():
    """Test the data processor with sample files."""
    print("Testing DataProcessor...")

    # Create temporary directory with test files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files with different encodings and formats
        test_files = [
            ("test.txt", "This is a test file with some content."),
            ("test.py", "def hello():\n    return 'Hello, World!'"),
            ("test.md", "# Test Markdown\n\nThis is a **test** markdown file."),
            ("test.json", '{"test": "data", "number": 42}'),
        ]

        for filename, content in test_files:
            (temp_path / filename).write_text(content, encoding="utf-8")

        # Test data processor
        from buddy.train import DataProcessor

        processor = DataProcessor(min_text_length=5, max_text_length=1000)
        processed_data = processor.process_directory(str(temp_path))

        print(f"✅ Processed {processed_data.stats['processed_files']} files")
        print(f"✅ Generated {processed_data.stats['total_texts']} text chunks")
        print(f"✅ Total characters: {processed_data.stats['total_characters']}")

        assert processed_data.stats["processed_files"] > 0
        assert len(processed_data.texts) > 0

        return True


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:
        from buddy.train import BuddyTrainedModel, DataProcessor, ModelManager, ModelTrainer, create_trained_model

        print("✅ All train modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Running Buddy Train Tests")
    print("=" * 40)

    tests = [
        test_imports,
        test_data_processor,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
                print(f"✅ {test.__name__} passed\n")
            else:
                failed += 1
                print(f"❌ {test.__name__} failed\n")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} failed with error: {e}\n")

    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
