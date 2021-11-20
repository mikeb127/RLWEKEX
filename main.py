from RLWEKEX import *

# These two Python scripts/project are an implementation of the RWLE-KEX as discussed here:

# https://en.wikipedia.org/wiki/Ring_learning_with_errors_key_exchange

# It's obviously designed to be a demonstration of the mathematical concepts involved and is not a
# crypto-secure implementation designed for production use etc.

# Setup the exchange, generate the shared value 'a' and generate public values
alice = RLWE_KEX(q=3079, n=32, b=5)
alice_public, alice_a = alice.calculate_public()
bob = RLWE_KEX(q=3079, n=32, b=5, a=alice_a)
bob_public = bob.calculate_public()

# The public values for Bob and Alice will be:
# A_public = A_sa + 2A_e
# B_public = B_sa + 2B_e

# Alice and Bob generate their private values using each others public values
alice.calculate_private(bob_public[0])
bob.calculate_private(alice_public)

# So now both Bob and Alice have generated private values that are approximately equal.
# These are:
# A_private = A_saB_s + 2B_eA_s + 2A_e1
# B_private = B_saA_s + 2A_eB_s + 2B_e1

# We need to generate the signal value and use it with the reconciliation function on the private values so we
# have an identical key stream
signal_info = alice.generate_signal()
alice.reconcile_key()
bob.reconcile_key(signal_info)

# Finally, we check if the key streams are the same
print(bob.get_key_stream())
print(alice.get_key_stream())
