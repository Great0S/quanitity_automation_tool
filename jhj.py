import math

# Example source data (mix of ints and floats)
source_values = [129, 128.99699988899, 135.5, 140]

# Example target data (mostly floats, reduced by 10%)
target_values = [value * 0.9 for value in source_values]

# Example: Adding 10% to each target value to compare with source values
adjusted_target_values = [value * 1.1 for value in target_values]

# Compare each adjusted target value with the corresponding source value
for source_val, target_val in zip(source_values, adjusted_target_values):
    if math.isclose(source_val, target_val, rel_tol=1e-9):
        print(f"Adjusted target value {target_val} is approximately equal to source value {source_val}")
    else:
        print(f"Adjusted target value {target_val} is not approximately equal to source value {source_val}")
