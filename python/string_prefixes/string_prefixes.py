print("\nDemonstrations of r-, b-, and f-strings")
print("========================================")

print("\nr-strings and f-strings. also, escaping and printing braces")
print("-----------------------------------------------------------")
my_numbers = "{1, 1, 2, 3, 5, 8}"
fr_test = (
    rf'The variable named my_numbers holds the value "{my_numbers}" '
    rf"and was verified by {{29843ed8-80d6-40a4-89e4-deb830f34d9f}}."
)
rf_test = (
    rf'The variable named my_numbers holds the value "{my_numbers}" '
    rf"and was verified by {{29843ed8-80d6-40a4-89e4-deb830f34d9f}}."
)
print(f"fr_test: {fr_test}")
print(f"rf_test: {rf_test}")
print("Both create the same object:", fr_test == rf_test)

print("\nr-strings and b-strings")
print("-----------------------")
# Test bytes + raw combinations
br_test = rb"Hello\nWorld"
rb_test = rb"Hello\nWorld"
print(f"br_test: {br_test}")
print(f"rb_test: {rb_test}")
print("Both create the same bytes object:", br_test == rb_test)

# Test case sensitivity (this should fail)
# Test escaping braces
print("\nTesting case-sensitivity of 'f-' specifier for f-strings")
print("--------------------------------------------------------")

test_type = "Uppercase F specifier"
# fmt: off
try:
    print(F"{test_type} succeeded")
except Exception as e:
    print(F"{test_type} failed")
    raise (e)
# fmt: on
