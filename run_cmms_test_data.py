#!/usr/bin/env python
"""
Simple script to run CMMS test data generation
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Import and run the generator
from CMMS_Test_Data_Generator import CMSTestDataGenerator

if __name__ == "__main__":
    print("🚀 Starting CMMS Test Data Generation...")
    generator = CMSTestDataGenerator()
    generator.run_all()
    print("\n✅ Test data generation completed successfully!")
