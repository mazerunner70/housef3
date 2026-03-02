# Phase 1 Review: Criteria Builder UX Design

## Overview

During Phase 1 review, users need to verify ML-detected patterns and refine the matching criteria that will power Phase 2 auto-categorization. The key challenge: **help users create accurate matching rules without understanding regex or technical patterns**.

## Core UX Principles

### 1. **Show, Don't Tell**
- Display all matched transactions visually
- Highlight what's common across them
- Show which parts vary
- Let users see the pattern themselves

### 2. **Progressive Disclosure**
- Start with automatic suggestions
- Allow refinement only if needed
- Hide technical complexity
- Show regex only to advanced users

### 3. **Real-Time Validation**
- Show match count as criteria change
- Highlight which transactions match/don't match
- Visual feedback (green/red indicators)
- Warn before creating too loose/tight criteria

### 4. **Learn from Examples**
- Extract patterns from matched transactions
- Suggest criteria based on commonality
- Show edge cases and outliers
- Let users include/exclude specific transactions

## Field-by-Field Criteria Mapping

### Merchant Pattern Field

#### What We're Extracting
From matched transactions like:
```
NETFLIX.COM STREAMING
NETFLIX COM
NETFLIX SUBSCRIPTION
NETFLIX.COM
```

We need to create a pattern that:
- Matches all these variations
- Doesn't match "NETFLIX GIFT CARD" or "NETFLIX DVD"

#### UX Design

```
┌─────────────────────────────────────────────────────────────┐
│ Merchant Pattern                                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Found in matched transactions:                               │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ NETFLIX.COM STREAMING           ✓ Matched                ││
│ │ NETFLIX COM                     ✓ Matched                ││
│ │ NETFLIX SUBSCRIPTION            ✓ Matched                ││
│ │ NETFLIX.COM                     ✓ Matched                ││
│ │                                                          ││
│ │ Common text: "NETFLIX"                                   ││
│ │ Variations: .COM, STREAMING, SUBSCRIPTION                ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ Matching Rule:                                               │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Contains: [NETFLIX                            ▼]         ││
│ │                                                          ││
│ │ ○ Exact match only                                       ││
│ │ ● Contains this text (ignore case)                       ││
│ │ ○ Starts with this text                                  ││
│ │ ○ Advanced (regex) [Show]                                ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ Exclude words (optional):                                    │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ GIFT CARD [×]   DVD [×]   [+ Add exclusion]              ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ Preview: Will match "NETFLIX" but not "NETFLIX GIFT CARD"   │
│                                                              │
│ ⚡ Test against all transactions: 12 matched  ✓             │
│                                                              │
│ [Advanced Options ▼]                                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Implementation Details

```python
class MerchantCriteriaBuilder:
    """Helps users build merchant matching criteria from examples."""
    
    @staticmethod
    def extract_common_pattern(descriptions: List[str]) -> dict:
        """
        Analyze matched transaction descriptions to find common patterns.
        
        Returns:
            {
                'common_substring': 'NETFLIX',
                'common_prefix': 'NETFLIX',
                'common_suffix': None,
                'variations': ['COM', 'STREAMING', 'SUBSCRIPTION'],
                'suggested_pattern': 'NETFLIX',
                'suggested_exclusions': [],
                'match_type': 'contains'  # or 'exact', 'prefix', 'suffix'
            }
        """
        if not descriptions:
            return {}
        
        # Normalize all descriptions
        normalized = [d.upper().strip() for d in descriptions]
        
        # Find longest common substring
        common_substring = MerchantCriteriaBuilder._find_longest_common_substring(
            normalized
        )
        
        # Check if they all start with the same text
        common_prefix = MerchantCriteriaBuilder._find_common_prefix(normalized)
        
        # Check if they all end with the same text
        common_suffix = MerchantCriteriaBuilder._find_common_suffix(normalized)
        
        # Extract variations (parts that differ)
        variations = MerchantCriteriaBuilder._find_variations(
            normalized, common_substring
        )
        
        # Determine best match type
        match_type = 'contains'
        suggested_pattern = common_substring
        
        if len(common_prefix) >= 5:  # Meaningful prefix
            match_type = 'prefix'
            suggested_pattern = common_prefix
        elif len(common_substring) >= 3:
            match_type = 'contains'
            suggested_pattern = common_substring
        
        return {
            'common_substring': common_substring,
            'common_prefix': common_prefix,
            'common_suffix': common_suffix,
            'variations': variations,
            'suggested_pattern': suggested_pattern,
            'suggested_exclusions': [],
            'match_type': match_type,
            'confidence': MerchantCriteriaBuilder._calculate_confidence(
                normalized, suggested_pattern
            )
        }
    
    @staticmethod
    def _find_longest_common_substring(strings: List[str]) -> str:
        """Find the longest substring common to all strings."""
        if not strings:
            return ""
        
        shortest = min(strings, key=len)
        
        for length in range(len(shortest), 0, -1):
            for start in range(len(shortest) - length + 1):
                substring = shortest[start:start + length]
                if all(substring in s for s in strings):
                    return substring
        
        return ""
    
    @staticmethod
    def _find_common_prefix(strings: List[str]) -> str:
        """Find common prefix of all strings."""
        if not strings:
            return ""
        
        prefix = strings[0]
        for s in strings[1:]:
            while not s.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    return ""
        return prefix
    
    @staticmethod
    def _find_common_suffix(strings: List[str]) -> str:
        """Find common suffix of all strings."""
        if not strings:
            return ""
        
        # Reverse strings, find prefix, reverse back
        reversed_strings = [s[::-1] for s in strings]
        reversed_suffix = MerchantCriteriaBuilder._find_common_prefix(reversed_strings)
        return reversed_suffix[::-1]
    
    @staticmethod
    def _find_variations(strings: List[str], common: str) -> List[str]:
        """Find unique variations after removing common part."""
        variations = set()
        for s in strings:
            # Remove common part and extract what's left
            remaining = s.replace(common, '').strip()
            if remaining:
                # Split by common separators
                parts = remaining.replace('.', ' ').replace('-', ' ').split()
                variations.update(parts)
        
        return sorted(list(variations))
    
    @staticmethod
    def _calculate_confidence(strings: List[str], pattern: str) -> float:
        """Calculate confidence that pattern is meaningful."""
        if not pattern:
            return 0.0
        
        # Higher confidence for longer patterns
        length_score = min(len(pattern) / 10, 1.0)
        
        # Higher confidence if pattern appears in same position
        positions = [s.find(pattern) for s in strings]
        position_variance = max(positions) - min(positions)
        position_score = 1.0 - (position_variance / 100)
        
        return (length_score + position_score) / 2
    
    @staticmethod
    def build_matching_function(
        pattern: str,
        match_type: str,
        exclusions: List[str] = None,
        case_sensitive: bool = False
    ) -> callable:
        """
        Build a function that matches descriptions based on criteria.
        
        Args:
            pattern: The text pattern to match
            match_type: 'contains', 'exact', 'prefix', 'suffix', or 'regex'
            exclusions: Words that disqualify a match
            case_sensitive: Whether matching is case-sensitive
            
        Returns:
            Function that takes a description and returns True/False
        """
        exclusions = exclusions or []
        
        def matcher(description: str) -> bool:
            # Normalize
            desc = description if case_sensitive else description.upper()
            pat = pattern if case_sensitive else pattern.upper()
            excl = exclusions if case_sensitive else [e.upper() for e in exclusions]
            
            # Check exclusions first
            if any(ex in desc for ex in excl):
                return False
            
            # Apply match type
            if match_type == 'exact':
                return desc == pat
            elif match_type == 'contains':
                return pat in desc
            elif match_type == 'prefix':
                return desc.startswith(pat)
            elif match_type == 'suffix':
                return desc.endswith(pat)
            elif match_type == 'regex':
                import re
                try:
                    return bool(re.search(pat, desc))
                except re.error:
                    return False
            
            return False
        
        return matcher
    
    @staticmethod
    def to_regex_pattern(
        pattern: str,
        match_type: str,
        exclusions: List[str] = None,
        case_sensitive: bool = False
    ) -> str:
        """
        Convert simple pattern to regex (for storage/advanced users).
        
        This is what gets stored in the database and used by Phase 2.
        """
        import re
        
        # Escape special regex characters in pattern
        escaped_pattern = re.escape(pattern)
        
        exclusions = exclusions or []
        
        # Build regex based on match type
        if match_type == 'exact':
            regex = f"^{escaped_pattern}$"
        elif match_type == 'contains':
            regex = escaped_pattern
        elif match_type == 'prefix':
            regex = f"^{escaped_pattern}"
        elif match_type == 'suffix':
            regex = f"{escaped_pattern}$"
        elif match_type == 'regex':
            regex = pattern  # Already a regex
        else:
            regex = escaped_pattern
        
        # Add negative lookahead for exclusions
        if exclusions:
            # Create pattern that fails if any exclusion is found
            escaped_exclusions = [re.escape(ex) for ex in exclusions]
            exclusion_pattern = '|'.join(escaped_exclusions)
            regex = f"(?!.*({exclusion_pattern})).*{regex}"
        
        # Add case-insensitive flag if needed
        if not case_sensitive:
            regex = f"(?i){regex}"
        
        return regex
```

### Amount Pattern Field

#### UX Design

```
┌─────────────────────────────────────────────────────────────┐
│ Amount Pattern                                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Amounts in matched transactions:                             │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Transaction    Amount    Deviation from Average          ││
│ │ ────────────────────────────────────────────────────────││
│ │ 2024-01-15    $14.99    ●─────────────────── (0%)        ││
│ │ 2024-02-15    $14.99    ●─────────────────── (0%)        ││
│ │ 2024-03-15    $14.99    ●─────────────────── (0%)        ││
│ │ 2024-04-15    $15.99    ──────●──────────── (+6.7%)      ││
│ │ 2024-05-15    $15.99    ──────●──────────── (+6.7%)      ││
│ │                                                          ││
│ │ Average: $15.19    Range: $14.99 - $15.99               ││
│ │ Standard Deviation: $0.45                                ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ Matching Rule:                                               │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Expected Amount: $15.19                                  ││
│ │                                                          ││
│ │ Tolerance: ±10% ───●───── = $13.67 to $16.71            ││
│ │            0%  5%  10% 15% 20% 25%                       ││
│ │                                                          ││
│ │ ✓ All matched transactions within tolerance             ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ Or use exact range:                                          │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Minimum: $14.99    Maximum: $15.99                       ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ ⚡ Test: 12 of 12 matched transactions within range  ✓      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Implementation

```python
class AmountCriteriaBuilder:
    """Helps users build amount matching criteria from examples."""
    
    @staticmethod
    def analyze_amounts(amounts: List[Decimal]) -> dict:
        """
        Analyze matched transaction amounts to suggest criteria.
        
        Returns:
            {
                'mean': Decimal('15.19'),
                'std': Decimal('0.45'),
                'min': Decimal('14.99'),
                'max': Decimal('15.99'),
                'suggested_tolerance_pct': Decimal('10.0'),
                'all_identical': False,
                'has_outliers': False,
                'outlier_indices': []
            }
        """
        if not amounts:
            return {}
        
        amounts_array = np.array([float(a) for a in amounts])
        
        mean = Decimal(str(np.mean(amounts_array)))
        std = Decimal(str(np.std(amounts_array)))
        min_amt = min(amounts)
        max_amt = max(amounts)
        
        # Check if all identical
        all_identical = len(set(amounts)) == 1
        
        # Suggest tolerance based on variation
        if all_identical:
            suggested_tolerance = Decimal("5.0")  # Small tolerance for identical amounts
        else:
            # Calculate natural variation
            variation_pct = (std / mean * 100) if mean > 0 else Decimal("10.0")
            # Round up to nearest 5%
            suggested_tolerance = Decimal(str(int(float(variation_pct) + 4.99) // 5 * 5))
            suggested_tolerance = max(Decimal("5.0"), min(suggested_tolerance, Decimal("25.0")))
        
        # Detect outliers (values > 2 std from mean)
        outlier_indices = []
        if std > 0:
            for i, amt in enumerate(amounts):
                z_score = abs((float(amt) - float(mean)) / float(std))
                if z_score > 2:
                    outlier_indices.append(i)
        
        return {
            'mean': mean,
            'std': std,
            'min': min_amt,
            'max': max_amt,
            'suggested_tolerance_pct': suggested_tolerance,
            'all_identical': all_identical,
            'has_outliers': len(outlier_indices) > 0,
            'outlier_indices': outlier_indices
        }
    
    @staticmethod
    def calculate_tolerance_range(
        mean: Decimal,
        tolerance_pct: Decimal
    ) -> tuple[Decimal, Decimal]:
        """Calculate min/max range from mean and tolerance percentage."""
        tolerance_amount = mean * (tolerance_pct / Decimal("100"))
        min_amount = mean - tolerance_amount
        max_amount = mean + tolerance_amount
        return min_amount, max_amount
    
    @staticmethod
    def test_tolerance_coverage(
        amounts: List[Decimal],
        mean: Decimal,
        tolerance_pct: Decimal
    ) -> dict:
        """Test how many amounts fall within tolerance."""
        min_amt, max_amt = AmountCriteriaBuilder.calculate_tolerance_range(
            mean, tolerance_pct
        )
        
        within_range = [amt for amt in amounts if min_amt <= amt <= max_amt]
        outside_range = [amt for amt in amounts if not (min_amt <= amt <= max_amt)]
        
        return {
            'total': len(amounts),
            'within_range': len(within_range),
            'outside_range': len(outside_range),
            'coverage_pct': (len(within_range) / len(amounts) * 100) if amounts else 0,
            'outside_amounts': outside_range
        }
```

### Date/Temporal Pattern Field

#### UX Design

```
┌─────────────────────────────────────────────────────────────┐
│ Date Pattern                                                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Dates in matched transactions:                               │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Calendar View:        [2024 ▼]                           ││
│ │                                                          ││
│ │ Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct  Nov   ││
│ │ ─15  ─15  ─15  ─16  ─15  ─15  ─15  ─14  ─15  ─16  ─15   ││
│ │  ●    ●    ●    ●    ●    ●    ●    ●    ●    ●    ●    ││
│ │                                                          ││
│ │ Pattern: Monthly around the 15th                         ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ Detected Pattern:                                            │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Frequency: ● Monthly   ○ Weekly   ○ Quarterly            ││
│ │                                                          ││
│ │ Timing:                                                  ││
│ │ ● Specific day of month: 15th  ± 2 days ───●─────       ││
│ │                                  0  1  2  3  4  5 days   ││
│ │                                                          ││
│ │ ○ Specific day of week: [Monday ▼]                       ││
│ │ ○ First working day of month                             ││
│ │ ○ Last working day of month                              ││
│ │ ○ Flexible (any time in period)                          ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ Date Distribution:                                           │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Day of Month:                                            ││
│ │  1   5   10  15  20  25  30                              ││
│ │                   ██                                     ││
│ │                  ████                                    ││
│ │                  ████                                    ││
│ │  └───┴────┴────┴────┴────┴────┴──                        ││
│ │                                                          ││
│ │ 9 transactions on day 15 ± 2 days                        ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ ⚡ Test: 12 of 12 matched transactions fit pattern  ✓       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Implementation

```python
class TemporalCriteriaBuilder:
    """Helps users build temporal matching criteria from examples."""
    
    @staticmethod
    def analyze_dates(dates: List[int]) -> dict:
        """
        Analyze transaction dates to detect temporal patterns.
        
        Args:
            dates: List of timestamps (milliseconds since epoch)
            
        Returns:
            {
                'frequency': RecurrenceFrequency.MONTHLY,
                'temporal_pattern_type': TemporalPatternType.DAY_OF_MONTH,
                'day_of_month': 15,
                'day_of_week': None,
                'suggested_tolerance_days': 2,
                'date_distribution': {...},
                'interval_analysis': {...}
            }
        """
        from datetime import datetime, timezone
        
        datetimes = [
            datetime.fromtimestamp(d / 1000, tz=timezone.utc) 
            for d in sorted(dates)
        ]
        
        # Analyze day of month distribution
        days_of_month = [dt.day for dt in datetimes]
        day_of_month_mode = max(set(days_of_month), key=days_of_month.count)
        day_of_month_variance = np.std(days_of_month) if len(days_of_month) > 1 else 0
        
        # Analyze day of week distribution
        days_of_week = [dt.weekday() for dt in datetimes]
        day_of_week_mode = max(set(days_of_week), key=days_of_week.count)
        day_of_week_consistency = days_of_week.count(day_of_week_mode) / len(days_of_week)
        
        # Analyze intervals between transactions
        intervals = []
        for i in range(1, len(datetimes)):
            delta = (datetimes[i] - datetimes[i-1]).days
            intervals.append(delta)
        
        avg_interval = np.mean(intervals) if intervals else 0
        interval_std = np.std(intervals) if len(intervals) > 1 else 0
        
        # Determine frequency
        frequency = TemporalCriteriaBuilder._detect_frequency(avg_interval)
        
        # Determine temporal pattern type
        pattern_type = TemporalPatternType.FLEXIBLE
        suggested_day = None
        
        if day_of_month_variance < 3:  # Consistent day of month
            pattern_type = TemporalPatternType.DAY_OF_MONTH
            suggested_day = day_of_month_mode
        elif day_of_week_consistency > 0.8:  # Consistent day of week
            pattern_type = TemporalPatternType.DAY_OF_WEEK
            suggested_day = day_of_week_mode
        
        # Suggest tolerance
        if pattern_type == TemporalPatternType.DAY_OF_MONTH:
            suggested_tolerance = max(2, int(day_of_month_variance * 2))
        else:
            suggested_tolerance = max(2, int(interval_std / 7))
        
        return {
            'frequency': frequency,
            'temporal_pattern_type': pattern_type,
            'day_of_month': day_of_month_mode if pattern_type == TemporalPatternType.DAY_OF_MONTH else None,
            'day_of_week': day_of_week_mode if pattern_type == TemporalPatternType.DAY_OF_WEEK else None,
            'suggested_tolerance_days': suggested_tolerance,
            'date_distribution': {
                'days_of_month': days_of_month,
                'days_of_week': days_of_week,
                'day_of_month_mode': day_of_month_mode,
                'day_of_week_mode': day_of_week_mode
            },
            'interval_analysis': {
                'avg_interval_days': avg_interval,
                'interval_std': interval_std,
                'intervals': intervals
            }
        }
    
    @staticmethod
    def _detect_frequency(avg_interval_days: float) -> RecurrenceFrequency:
        """Detect frequency from average interval."""
        if avg_interval_days < 2:
            return RecurrenceFrequency.DAILY
        elif 5 <= avg_interval_days <= 9:
            return RecurrenceFrequency.WEEKLY
        elif 12 <= avg_interval_days <= 16:
            return RecurrenceFrequency.BI_WEEKLY
        elif 27 <= avg_interval_days <= 33:
            return RecurrenceFrequency.MONTHLY
        elif 58 <= avg_interval_days <= 65:
            return RecurrenceFrequency.BI_MONTHLY
        elif 85 <= avg_interval_days <= 95:
            return RecurrenceFrequency.QUARTERLY
        elif 175 <= avg_interval_days <= 195:
            return RecurrenceFrequency.SEMI_ANNUALLY
        elif 350 <= avg_interval_days <= 380:
            return RecurrenceFrequency.ANNUALLY
        else:
            return RecurrenceFrequency.IRREGULAR
```

## Complete Interactive Criteria Builder

### Main Review Interface

```
┌───────────────────────────────────────────────────────────────────┐
│ Review Recurring Pattern                                   [1/3] │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│ ┌───────────────────────────────────────────────────────────────┐│
│ │ 📊 Pattern Summary                                            ││
│ │                                                               ││
│ │ Detected: Monthly subscription charge                        ││
│ │ Confidence: 94% ████████████████████░░                       ││
│ │ Transactions: 12 matches over 11 months                      ││
│ └───────────────────────────────────────────────────────────────┘│
│                                                                   │
│ ┌───────────────────────────────────────────────────────────────┐│
│ │ 🔍 Matched Transactions                          [Show All ▼]││
│ │                                                               ││
│ │ Date       Description              Amount    Account        ││
│ │ ──────────────────────────────────────────────────────────── ││
│ │ 2024-11-15 NETFLIX.COM STREAMING   $15.99    Chase Visa     ││
│ │ 2024-10-15 NETFLIX COM             $15.99    Chase Visa     ││
│ │ 2024-09-15 NETFLIX SUBSCRIPTION    $14.99    Chase Visa     ││
│ │ ...                                                           ││
│ │                                                               ││
│ │ [View Transaction Details]                                    ││
│ └───────────────────────────────────────────────────────────────┘│
│                                                                   │
│ ┌───────────────────────────────────────────────────────────────┐│
│ │ ⚙️ Matching Criteria                                          ││
│ │                                                               ││
│ │ These rules will identify future matching transactions:      ││
│ │                                                               ││
│ │ ┌─────────────────────────────────────────────────────────┐  ││
│ │ │ 1. Merchant Pattern              [Auto-detected ✓] [Edit]││
│ │ │                                                         │  ││
│ │ │    Contains: "NETFLIX"           (case insensitive)     │  ││
│ │ │    Excludes: "GIFT CARD", "DVD"                         │  ││
│ │ │                                                         │  ││
│ │ │    ✓ Matches all 12 transactions                        │  ││
│ │ └─────────────────────────────────────────────────────────┘  ││
│ │                                                               ││
│ │ ┌─────────────────────────────────────────────────────────┐  ││
│ │ │ 2. Amount Pattern                [Auto-detected ✓] [Edit]││
│ │ │                                                         │  ││
│ │ │    Expected: $15.19                                     │  ││
│ │ │    Tolerance: ± 10% ($13.67 - $16.71)                  │  ││
│ │ │                                                         │  ││
│ │ │    ✓ Matches all 12 transactions                        │  ││
│ │ └─────────────────────────────────────────────────────────┘  ││
│ │                                                               ││
│ │ ┌─────────────────────────────────────────────────────────┐  ││
│ │ │ 3. Date Pattern                  [Auto-detected ✓] [Edit]││
│ │ │                                                         │  ││
│ │ │    Frequency: Monthly                                   │  ││
│ │ │    Expected: 15th of month ± 2 days                    │  ││
│ │ │                                                         │  ││
│ │ │    ✓ Matches all 12 transactions                        │  ││
│ │ └─────────────────────────────────────────────────────────┘  ││
│ │                                                               ││
│ │ ┌─────────────────────────────────────────────────────────┐  ││
│ │ │ 4. Category Assignment           [Select]               ││
│ │ │                                                         │  ││
│ │ │    [Entertainment ▼] > [Streaming ▼]                   │  ││
│ │ └─────────────────────────────────────────────────────────┘  ││
│ └───────────────────────────────────────────────────────────────┘│
│                                                                   │
│ ┌───────────────────────────────────────────────────────────────┐│
│ │ 🧪 Test Criteria                                              ││
│ │                                                               ││
│ │ Your criteria will match:                                     ││
│ │                                                               ││
│ │ ✓ All 12 original transactions                                ││
│ │ ✓ 0 additional transactions                                   ││
│ │                                                               ││
│ │ Status: 🟢 Perfect match - Ready to activate                  ││
│ └───────────────────────────────────────────────────────────────┘│
│                                                                   │
│ Actions:                                                          │
│ [✓ Confirm & Activate]  [✓ Confirm Only]  [Edit]  [✗ Reject]   │
│                                                                   │
│                                   [< Previous]  [Next Pattern >] │
└───────────────────────────────────────────────────────────────────┘
```

## Data Flow: UI to Database

### What User Sees → What Gets Stored

```python
# User Interface Layer
user_criteria = {
    'merchant': {
        'pattern': 'NETFLIX',
        'match_type': 'contains',
        'case_sensitive': False,
        'exclusions': ['GIFT CARD', 'DVD']
    },
    'amount': {
        'expected': Decimal('15.19'),
        'tolerance_pct': Decimal('10.0')
    },
    'temporal': {
        'frequency': 'monthly',
        'pattern_type': 'day_of_month',
        'day': 15,
        'tolerance_days': 2
    }
}

# Conversion Layer (Backend Service)
def convert_user_criteria_to_pattern(
    user_criteria: dict,
    matched_transactions: List[Transaction]
) -> RecurringChargePattern:
    """Convert user-friendly criteria to database format."""
    
    # Build merchant pattern (with regex if needed for exclusions)
    merchant_pattern = MerchantCriteriaBuilder.to_regex_pattern(
        pattern=user_criteria['merchant']['pattern'],
        match_type=user_criteria['merchant']['match_type'],
        exclusions=user_criteria['merchant']['exclusions'],
        case_sensitive=user_criteria['merchant']['case_sensitive']
    )
    
    # Calculate amount statistics
    amounts = [abs(tx.amount) for tx in matched_transactions]
    amount_mean = Decimal(str(np.mean([float(a) for a in amounts])))
    amount_std = Decimal(str(np.std([float(a) for a in amounts])))
    amount_min = min(amounts)
    amount_max = max(amounts)
    
    # Create pattern
    pattern = RecurringChargePattern(
        userId=user_id,
        merchantPattern=merchant_pattern,  # Regex stored for Phase 2
        frequency=RecurrenceFrequency(user_criteria['temporal']['frequency']),
        temporalPatternType=TemporalPatternType(user_criteria['temporal']['pattern_type']),
        dayOfMonth=user_criteria['temporal'].get('day'),
        toleranceDays=user_criteria['temporal']['tolerance_days'],
        amountMean=amount_mean,
        amountStd=amount_std,
        amountMin=amount_min,
        amountMax=amount_max,
        amountTolerancePct=user_criteria['amount']['tolerance_pct'],
        confidenceScore=Decimal('0.95'),
        transactionCount=len(matched_transactions),
        firstOccurrence=matched_transactions[0].date,
        lastOccurrence=matched_transactions[-1].date,
        matchedTransactionIds=[tx.transaction_id for tx in matched_transactions],
        status=PatternStatus.CONFIRMED,
        active=False  # Not auto-categorizing yet
    )
    
    return pattern

# Database Storage
{
    'patternId': 'uuid-string',
    'userId': 'user123',
    'merchantPattern': '(?i)(?!.*(GIFT CARD|DVD)).*NETFLIX',  # Regex for Phase 2
    'frequency': 'monthly',
    'temporalPatternType': 'day_of_month',
    'dayOfMonth': 15,
    'toleranceDays': 2,
    'amountMean': Decimal('15.19'),
    'amountTolerancePct': Decimal('10.0'),
    'matchedTransactionIds': ['tx-uuid-1', 'tx-uuid-2', ...],  # Phase 1 record
    'status': 'confirmed',
    'active': 'false'
}
```

## Best Practices Implementation

### 1. **Visual Feedback Loop**

```python
class CriteriaValidator:
    """Provides real-time validation as user adjusts criteria."""
    
    def validate_in_real_time(
        self,
        current_criteria: dict,
        original_transactions: List[Transaction],
        all_user_transactions: List[Transaction]
    ) -> dict:
        """
        Called on every criteria change (debounced).
        
        Returns instant feedback about match quality.
        """
        # Apply criteria to original cluster
        original_matches = self._apply_criteria(
            current_criteria, original_transactions
        )
        
        # Apply criteria to ALL transactions
        all_matches = self._apply_criteria(
            current_criteria, all_user_transactions
        )
        
        original_ids = {tx.transaction_id for tx in original_transactions}
        matched_ids = {tx.transaction_id for tx in all_matches}
        
        coverage = len(original_matches) / len(original_transactions) * 100
        extra = len(matched_ids - original_ids)
        
        # Determine status
        if coverage == 100 and extra == 0:
            status = 'perfect'
            message = '🟢 Perfect match - Ready to activate'
            color = 'green'
        elif coverage == 100:
            status = 'loose'
            message = f'🟡 Matches all originals + {extra} others - Consider tightening'
            color = 'yellow'
        elif coverage >= 80:
            status = 'acceptable'
            message = f'🟡 Matches {coverage:.0f}% of originals - Consider loosening'
            color = 'yellow'
        else:
            status = 'poor'
            message = f'🔴 Only matches {coverage:.0f}% of originals - Criteria too strict'
            color = 'red'
        
        return {
            'status': status,
            'message': message,
            'color': color,
            'coverage_pct': coverage,
            'original_matched': len(original_matches),
            'original_total': len(original_transactions),
            'extra_matched': extra,
            'can_activate': coverage >= 80  # Allow some flexibility
        }
```

### 2. **Progressive Disclosure**

```
Initial View:
┌──────────────────────────────┐
│ Merchant: NETFLIX     ✓      │
│ Amount: $15.19 ± 10%  ✓      │
│ Date: 15th monthly ± 2d ✓    │
│                              │
│ [Edit Criteria]              │
└──────────────────────────────┘

After clicking "Edit Criteria":
┌──────────────────────────────────────┐
│ Merchant Pattern                     │
│ ┌──────────────────────────────────┐ │
│ │ Contains: [NETFLIX        ▼]    │ │
│ │ ○ Exact  ● Contains  ○ Starts   │ │
│ │ Exclusions: [+ Add]              │ │
│ └──────────────────────────────────┘ │
│                                      │
│ [Show Advanced Options ▼]            │
└──────────────────────────────────────┘

After clicking "Show Advanced":
┌──────────────────────────────────────┐
│ Advanced Merchant Options            │
│ ┌──────────────────────────────────┐ │
│ │ □ Case sensitive matching        │ │
│ │ □ Use regex pattern              │ │
│ │                                  │ │
│ │ Regex Pattern:                   │ │
│ │ (?i)NETFLIX                      │ │
│ │                                  │ │
│ │ [Test Regex]                     │ │
│ └──────────────────────────────────┘ │
└──────────────────────────────────────┘
```

### 3. **Smart Defaults with Easy Override**

```python
class SmartDefaultsService:
    """Provides intelligent defaults that users can override."""
    
    def suggest_initial_criteria(
        self,
        matched_transactions: List[Transaction]
    ) -> dict:
        """
        Analyze matched transactions and suggest best criteria.
        
        Users can accept as-is or refine.
        """
        # Extract merchant pattern
        descriptions = [tx.description for tx in matched_transactions]
        merchant_analysis = MerchantCriteriaBuilder.extract_common_pattern(descriptions)
        
        # Analyze amounts
        amounts = [abs(tx.amount) for tx in matched_transactions]
        amount_analysis = AmountCriteriaBuilder.analyze_amounts(amounts)
        
        # Analyze dates
        dates = [tx.date for tx in matched_transactions]
        temporal_analysis = TemporalCriteriaBuilder.analyze_dates(dates)
        
        return {
            'merchant': {
                'pattern': merchant_analysis['suggested_pattern'],
                'match_type': merchant_analysis['match_type'],
                'case_sensitive': False,
                'exclusions': merchant_analysis['suggested_exclusions'],
                'confidence': merchant_analysis['confidence']
            },
            'amount': {
                'expected': amount_analysis['mean'],
                'tolerance_pct': amount_analysis['suggested_tolerance_pct'],
                'all_identical': amount_analysis['all_identical']
            },
            'temporal': {
                'frequency': temporal_analysis['frequency'].value,
                'pattern_type': temporal_analysis['temporal_pattern_type'].value,
                'day': temporal_analysis['day_of_month'],
                'tolerance_days': temporal_analysis['suggested_tolerance_days']
            }
        }
```

## Summary

### Key UX Principles
1. **Show Examples First**: Display matched transactions before asking for rules
2. **Auto-Detect**: ML suggests criteria from patterns in data
3. **Visual Validation**: Show real-time feedback as criteria change
4. **Simple by Default**: Hide complexity (regex) unless needed
5. **Test Before Save**: Always validate criteria before activation

### Phase 1 → Phase 2 Connection
- **Phase 1**: User builds criteria using simple UI (contains/exact/prefix + exclusions)
- **Backend**: Converts to regex and stores in `merchantPattern` field
- **Phase 2**: Uses stored regex for fast, consistent matching
- **Validation**: Ensures criteria match original cluster before activation

This approach makes pattern creation accessible to non-technical users while maintaining the power and flexibility needed for accurate auto-categorization.

