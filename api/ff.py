import numpy as np

# Input dimensions
X, Y = map(int, input().split())

# Input arrays
A = np.array([list(map(int, input().split())) for _ in range(X)])
B = np.array([list(map(int, input().split())) for _ in range(X)])

# Perform operations
print("Addition:")
print(A + B)

print("\nSubtraction:")
print(A - B)

print("\nMultiplication:")
print(A * B)

print("\nInteger Division:")
print(np.floor_divide(A, B))

print("\nMod:")
print(np.mod(A, B))

print("\nPower:")
print(np.power(A, B))
