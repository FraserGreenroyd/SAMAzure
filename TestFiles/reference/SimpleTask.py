import sys

A = sys.argv[1]

B = sys.argv[2]

with open("output.txt", "w") as f:
    f.write(A + B)
