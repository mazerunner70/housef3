#!/usr/bin/env python3
import sys
import os
from datetime import date, datetime, timedelta

# Add the backend/src directory to Python path
backend_src = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'backend', 'src')
sys.path.insert(0, backend_src)

from services.analytics_computation_engine import AnalyticsComputationEngine

def test_time_period_parsing():
    """Test various time period formats"""
    engine = AnalyticsComputationEngine()
    
    test_periods = [
        '12months',
        '3months',
        '2024-01',
        '2024-Q1',
        '2024',
        'overall'
    ]
    
    print("\nTesting time period parsing:")
    print("=" * 50)
    
    for period in test_periods:
        try:
            start_date, end_date = engine._parse_time_period(period)
            days = (end_date - start_date).days + 1
            print(f"\nPeriod: {period}")
            print(f"Start date: {start_date}")
            print(f"End date: {end_date}")
            print(f"Days in period: {days}")
        except Exception as e:
            print(f"\nError parsing {period}: {str(e)}")

if __name__ == "__main__":
    test_time_period_parsing() 