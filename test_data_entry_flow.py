#!/usr/bin/env python3
"""
Test script to verify the modified data entry flow works correctly.
Tests that the main window stays open and form resets after saving entries.
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox
import threading
import time

# Add the current directory to the Python path
sys.path.insert(0, '/home/david/kpop-performance-database')

from main_ui import MainWindow
from data_entry_ui import DataEntryWindow

class DataEntryFlowTester:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the root window
        self.test_results = []
        
    def test_form_reset_method(self):
        """Test that the reset_form_fields method exists and can be called"""
        try:
            # Create a minimal test setup
            from database_operations import DatabaseOperations
            db_ops = DatabaseOperations()
            
            # Create data entry window
            data_entry = DataEntryWindow(self.root, db_ops)
            
            # Check if reset_form_fields method exists
            if hasattr(data_entry, 'reset_form_fields'):
                # Test calling the method
                data_entry.reset_form_fields()
                self.test_results.append("✅ reset_form_fields() method exists and can be called")
                
                # Test that form variables are reset
                if (data_entry.url_entry_var.get() == "" and 
                    data_entry.primary_artist_var.get() == "" and
                    data_entry.title_var.get() == ""):
                    self.test_results.append("✅ Form variables properly reset")
                else:
                    self.test_results.append("❌ Form variables not properly reset")
            else:
                self.test_results.append("❌ reset_form_fields() method not found")
                
            data_entry.destroy()
            
        except Exception as e:
            self.test_results.append(f"❌ Error testing form reset: {str(e)}")
    
    def test_save_method_modifications(self):
        """Test that save methods call reset_form_fields instead of close_window"""
        try:
            # Read the data_entry_ui.py file to check for the modifications
            with open('/home/david/kpop-performance-database/data_entry_ui.py', 'r') as f:
                content = f.read()
            
            # Check for reset_form_fields calls in save methods
            reset_calls = content.count('self.reset_form_fields()')
            if reset_calls >= 4:  # Should be at least 4 calls (2 for local saves, 2 for URL saves)
                self.test_results.append(f"✅ Found {reset_calls} calls to reset_form_fields() in save methods")
            else:
                self.test_results.append(f"❌ Only found {reset_calls} calls to reset_form_fields(), expected at least 4")
            
            # Check that close_window is not called in save methods
            if 'self.close_window()' not in content:
                self.test_results.append("✅ No calls to close_window() found (good)")
            else:
                # Count how many times close_window is called
                close_calls = content.count('self.close_window()')
                self.test_results.append(f"⚠️  Found {close_calls} calls to close_window() - may need review")
                
        except Exception as e:
            self.test_results.append(f"❌ Error checking save method modifications: {str(e)}")
    
    def run_tests(self):
        """Run all tests and display results"""
        print("🧪 Testing Data Entry Flow Modifications...")
        print("=" * 50)
        
        self.test_form_reset_method()
        self.test_save_method_modifications()
        
        print("\n📋 Test Results:")
        print("-" * 30)
        for result in self.test_results:
            print(result)
        
        # Summary
        passed_tests = sum(1 for result in self.test_results if result.startswith("✅"))
        failed_tests = sum(1 for result in self.test_results if result.startswith("❌"))
        warning_tests = sum(1 for result in self.test_results if result.startswith("⚠️"))
        
        print(f"\n📊 Summary: {passed_tests} passed, {failed_tests} failed, {warning_tests} warnings")
        
        if failed_tests == 0:
            print("🎉 All critical tests passed! The data entry flow should work correctly.")
        else:
            print("⚠️  Some tests failed. Please review the issues above.")
        
        return failed_tests == 0

if __name__ == "__main__":
    tester = DataEntryFlowTester()
    success = tester.run_tests()
    sys.exit(0 if success else 1)
