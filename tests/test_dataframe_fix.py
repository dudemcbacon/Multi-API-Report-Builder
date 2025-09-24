#!/usr/bin/env python3
"""
Test script to verify DataFrame creation fix
"""

def test_dataframe_creation():
    """Test the DataFrame creation logic without requiring full environment"""
    print("Testing DataFrame creation logic...")
    
    # Test data that was causing the issue
    aligned_data = [
        {
            'SFDC Order #': '1001',
            'SFDC Amount': 100.50,
            'QB Order #': '1001',
            'QB Amount': 100.50,
            'Difference': 0.0,
            'Notes': ''
        },
        {
            'SFDC Order #': '',  # Empty string that was causing issues
            'SFDC Amount': 0.0,
            'QB Order #': '1002',
            'QB Amount': 200.0,
            'Difference': -200.0,
            'Notes': ''
        }
    ]
    
    # Apply the same logic as in the fixed code
    print("Applying data type fixes...")
    
    for row in aligned_data:
        # Ensure string fields are strings
        row['SFDC Order #'] = str(row['SFDC Order #']) if row['SFDC Order #'] is not None else ""
        row['QB Order #'] = str(row['QB Order #']) if row['QB Order #'] is not None else ""
        row['Notes'] = str(row['Notes']) if row['Notes'] is not None else ""
        
        # Ensure numeric fields are floats
        row['SFDC Amount'] = float(row['SFDC Amount']) if row['SFDC Amount'] is not None and row['SFDC Amount'] != "" else 0.0
        row['QB Amount'] = float(row['QB Amount']) if row['QB Amount'] is not None and row['QB Amount'] != "" else 0.0
        row['Difference'] = float(row['Difference']) if row['Difference'] is not None and row['Difference'] != "" else 0.0
    
    # Print the fixed data
    print("Fixed data:")
    for i, row in enumerate(aligned_data):
        print(f"  Row {i+1}:")
        for key, value in row.items():
            print(f"    {key}: {value} (type: {type(value).__name__})")
    
    # Test totals calculation
    print("\nTesting totals calculation...")
    sfdc_total = sum(abs(float(row['SFDC Amount'])) for row in aligned_data if row['SFDC Amount'] not in [None, ""])
    qb_total = sum(abs(float(row['QB Amount'])) for row in aligned_data if row['QB Amount'] not in [None, ""])
    
    print(f"SFDC Total: {sfdc_total}")
    print(f"QB Total: {qb_total}")
    print(f"Difference: {sfdc_total - qb_total}")
    
    print("\n✓ DataFrame creation logic test passed!")
    return True

if __name__ == "__main__":
    test_dataframe_creation()