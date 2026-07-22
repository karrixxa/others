import sys
import time
import os
import gmpy2
from concurrent.futures import ProcessPoolExecutor
from gmpy2 import mpz, mpfr, sqrt

sys.set_int_max_str_digits(0)

def bs_worker(args):
    start, end = args
    P_list, Q_list, T_list = [], [], []
    for k in range(start, end):
        mk = mpz(k)
        P = (6*mk - 5) * (2*mk - 1) * (6*mk - 1)
        Q = mk**3 - 16*mk
        T = mpz(13591409) + mpz(545140134) * mk
        if k % 2 == 1: T = -T
        P_list.append(P); Q_list.append(Q); T_list.append(T)
    while len(P_list) > 1:
        next_P, next_Q, next_T = [], [], []
        for i in range(0, len(P_list), 2):
            if i + 1 < len(P_list):
                P1, Q1, T1 = P_list[i], Q_list[i], T_list[i]
                P2, Q2, T2 = P_list[i+1], Q_list[i+1], T_list[i+1]
                next_P.append(P1 * P2); next_Q.append(Q1 * Q2); next_T.append(T1 * Q2 + P1 * T2)
            else:
                next_P.append(P_list[i]); next_Q.append(Q_list[i]); next_T.append(T_list[i])
        P_list, Q_list, T_list = next_P, next_Q, next_T
    return P_list[0], Q_list[0], T_list[0]

def tree_merge(results):
    while len(results) > 1:
        next_level = []
        for i in range(0, len(results), 2):
            if i + 1 < len(results):
                P1, Q1, T1 = results[i]; P2, Q2, T2 = results[i+1]
                next_level.append((P1 * P2, Q1 * Q2, T1 * Q2 + P1 * T2))
            else: next_level.append(results[i])
        results = next_level
    return results[0]

def compute_pi(digits, workers=None):
    if workers is None: workers = os.cpu_count() or 1
    precision_bits = int(digits * 3.321928094887362) + 128
    gmpy2.get_context().precision = precision_bits
    num_terms = (digits // 14) + 1
    chunk_size = (num_terms // workers) + 1
    tasks = [(i, min(i + chunk_size, num_terms)) for i in range(0, num_terms, chunk_size)]
    with ProcessPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(bs_worker, tasks))
    P_final, Q_final, T_final = tree_merge(results)
    C_const, S_10005 = mpfr(426976), sqrt(mpfr(10005))
    return (C_const * S_10005 * mpfr(Q_final)) / (mpfr(12) * mpfr(T_final))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--digits", type=int, default=10_000_000)
    args = parser.parse_args()
    start = time.perf_counter()
    result = compute_pi(args.digits)
    duration = time.perf_counter() - start
    print(f"Digits: {args.digits} | Time: {duration:.4f}s | Rate: {(args.digits/duration)*60:,.2f} dig/min")
