from numpy.polynomial import Polynomial
import numpy as np
import random


class RLWE_KEX:

    def __init__(self, q, n, b, a=None):

        self.b = b
        self.n = n
        self.q = q
        if a is None:
            self.a = self.generate_a()
        else:
            self.a = a
        self.e = self.get_random_poly()
        self.e1 = self.get_random_poly()
        self.s = self.get_random_poly()
        self.p = None
        self.w = None
        self.k = None
        self.key_stream = None

    def generate_a(self):
        # This method generates a random polynomial of highest degree n-1 with coefficients between 0 and q.

        # NOTE: This function is not really consistent with the RLWE-KEX setup. In the relevant paper
        # the setup is conducted by generating a polynomial based on a seed using the SHAKE128 function.
        # Because I'm lazy and don't really want to implement that, the coefficients are random
        # uniform sample for this.

        # Params: Output : a - generated polynomial

        a = np.zeros(self.n)
        for i in range(0, self.n):
            a[i] = random.randint(0, self.q)
        return Polynomial(a)

    def reduce_back_into_ring(self, poly):
        # This method reduces polynomials with terms of a higher degree back down so they are of a degree
        # included in the polynomial ring. This is step one of reduction back into the ring. The other is reducing
        # the coefficients. See reduce_coefficients for this.

        # For more information on polynomial rings try:
        # https://en.wikipedia.org/wiki/Polynomial_ring

        # Params: Input: poly - polynomial with terms of a higher degree than what is included in the
        #                polynomial ring
        #         Output: reduced_poly - polynomial with terms reduced into the ring

        indx = 0
        reduced_poly = np.zeros(self.n)
        a = poly.coef
        # Initialize the first n values
        for i in range(0, self.n):
            reduced_poly[i] = a[i]

        # Now iterate over the values of a higher degree and put them back where they belong
        for i in range(self.n, a.shape[0]):
            reduced_poly[indx] = reduced_poly[indx] + a[i]
            indx = indx + 1
            if indx >= self.n:
                indx = 0
        return Polynomial(reduced_poly)

    def reduce_coefficients(self, poly, mod_val):
        # This method reduces polynomial coefficients back into the ring. Everywhere else, this is referred to
        # to as a mod q reduction. It is actually a subset of this with it becoming-(q-1/2) through to (q-1)/2.

        # For more information on polynomial rings try:
        # https://en.wikipedia.org/wiki/Polynomial_ring

        # Params: Input: poly - polynomial with terms of a higher degree than what is included in the
        #                polynomial ring
        #                mod_val - value to be used for the reduction
        #         Output: ret_val - polynomial with terms reduced into the ring

        # Reduce coefficients mod q
        ret_val = Polynomial(poly.coef % mod_val)

        # Coerce back Zq. Note this is a subset of mod q. It becomes -(q-1/2) through to (q-1)/2.
        # This must be done to have the signal function work correctly.
        middle = (self.q - 1) / 2
        for i in range(0, ret_val.coef.shape[0]):
            if ret_val.coef[i] > middle:
                ret_val.coef[i] = ret_val.coef[i] - self.q
        return ret_val

    def add(self, poly1, poly2, mod_val):
        # This method performs addition within the polynomial ring.

        # Params: Input: poly1 - polynomial to be added
        #                poly2 - polynomial to be added
        #                mod_val - modulo value for reduction of the coefficients
        #         Output: add_result- resulting polynomial with terms reduced into the ring

        # Perform straight up addition of two polynomials not considering the ring
        add_result = Polynomial(poly1.coef + poly2.coef)
        # Reduce the coefficients mod q
        return self.reduce_coefficients(add_result, mod_val)

    def multiply(self, poly1, poly2, mod_val):
        # This method performs multiplication within the polynomial ring.

        # Params: Input: poly1 - polynomial to be multiplied
        #                poly2 - polynomial to be multiplied
        #                mod_val - modulo value for reduction of the coefficients
        #         Output: mul_result - resulting polynomial with terms reduced into the ring

        # Perform straight up multiplication of the two polynomials not considering the ring
        mul_result = poly1 * poly2
        # Reduce terms of a higher degree than what is included in the ring
        mul_result = self.reduce_back_into_ring(mul_result)
        # Reduce the coefficients mod q
        mul_result = self.reduce_coefficients(mul_result, mod_val)
        return mul_result

    def get_random_poly(self):
        # This method generates a random polynomial of highest degree n-1 with small coefficients between
        # b and -b. Currently hardcoded to b=5.

        # NOTE: Real world implementations probably use gaussian sampling techniques for the coefficients.
        # We will once again use random uniform sampling for simplicities sake.

        # Params: Output : a - generated polynomial

        b_list = [5, 4, 3, 2, 1, 0, -1, -2, -3, -4, -5]

        a = np.zeros(self.n)
        for i in range(0, self.n):
            rand_indx = random.randint(0, 9)
            a[i] = b_list[rand_indx]
        return Polynomial(a)

    def generate_signal(self):
        # This method generates the 'signal' to be used in the reconciliation function.

        # Params: Input: this_poly - polynomial to be used as input to the function
        #         Output: w_out - signal to be used for reconciliation

        w = self.k.coef
        w_out = np.ones(w.shape[0])
        up_bound = (self.q - 1) / 4
        low_bound = -1 * up_bound
        for i in range(0, w_out.shape[0]):
            if w[i] >= low_bound and w[i] <= up_bound:
                w_out[i] = 0
        self.w = Polynomial(w_out)
        return self.w

    def calc_mod2_reconciliation(self, w):
        # This method performs the reconciliation of the approximately equal secrets using the
        # 'signal'

        # Params: Input: w - signal for reconciliation

        q_scalar = ((self.q - 1) / 2)
        multiply_w = Polynomial(w.coef * q_scalar)
        ret_skr = self.add(self.k, multiply_w, self.q)
        self.key_stream = ret_skr.coef % 2

    def calculate_public(self):
        # This method calculates the public value of a party in the key exchange. It also returns the shared
        # value 'a' to allow it to be provided to the other party in the exchange.
        # Calculation for the public_value = sa + 2e
        # Params: Output: p - public value polynomial
        #                 a - public value shared between parties in the exchange

        self.p = self.add(self.multiply(self.a, self.s, self.q), Polynomial((2 * self.e.coef)), self.q)
        return self.p, self.a

    def calculate_private(self, p_in):
        # This method calculates the private value of a party in the key exchange.
        # Calculation for the private value = sp_in + 2e1
        # Params: Input: p_in - public value polynomial of other participant in the exchange

        self.k = self.add(self.multiply(p_in, self.s, self.q), Polynomial((2 * self.e1.coef)), self.q)

    def reconcile_key(self, w=None):
        # This method is just to delegate to the reconciliation function. Behaves slightly differently depending on
        # whether the party is the one who generated the signal, or whether they are the one receiving it.
        # Params: Input: w - input signal value. If provided assume 'receiving party' of signal

        if w is None:
            self.calc_mod2_reconciliation(self.w)
        else:
            self.calc_mod2_reconciliation(w)

    def get_key_stream(self):
        # Just returns the key stream so we can check correctness. Obviously wouldn't exist in the real world....

        return self.key_stream
