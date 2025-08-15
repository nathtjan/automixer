def levenshtein_distance(s1, s2):
    """Compute Levenshtein distance using only two rows (space-optimized)."""
    if len(s1) < len(s2):
        s1, s2 = s2, s1  # Ensure s1 is longer

    previous = list(range(len(s2) + 1))
    current = [0] * (len(s2) + 1)

    for i, c1 in enumerate(s1, 1):
        current[0] = i
        for j, c2 in enumerate(s2, 1):
            insert = current[j - 1] + 1
            delete = previous[j] + 1
            substitute = previous[j - 1] + (c1 != c2)
            current[j] = min(insert, delete, substitute)
        previous, current = current, previous  # Swap

    return previous[len(s2)]


def lcs(seq1, seq2):
    """Standard LCS for exact matches."""
    m, n = len(seq1), len(seq2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m):
        for j in range(n):
            if seq1[i] == seq2[j]:
                dp[i + 1][j + 1] = dp[i][j] + 1
            else:
                dp[i + 1][j + 1] = max(dp[i][j + 1], dp[i + 1][j])

    # Reconstruct LCS
    lcs = []
    i, j = m, n
    while i > 0 and j > 0:
        if seq1[i - 1] == seq2[j - 1]:
            lcs.append(seq1[i - 1])
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1

    return dp[m][n], lcs[::-1]


def lcs_1gram(seq1, seq2, tolerance=0):
    """
    Optimized 1-gram LCS using fast Levenshtein distance.
    Two words are equal if their distance <= tolerance.
    """
    m, n = len(seq1), len(seq2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    def equal_with_tolerance(a, b):
        if abs(len(a) - len(b)) > tolerance:
            return False
        return levenshtein_distance(a, b) <= tolerance

    # Fill DP table
    for i in range(m):
        for j in range(n):
            if equal_with_tolerance(seq1[i], seq2[j]):
                dp[i + 1][j + 1] = dp[i][j] + 1
            else:
                dp[i + 1][j + 1] = max(dp[i][j + 1], dp[i + 1][j])

    # Reconstruct LCS
    lcs = []
    i, j = m, n
    while i > 0 and j > 0:
        if equal_with_tolerance(seq1[i - 1], seq2[j - 1]):
            lcs.append(seq1[i - 1])  # or seq2[j - 1]
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1

    return dp[m][n], lcs[::-1]


# === EXAMPLE USAGE ===
if __name__ == "__main__":
    s1 = "the quick brown fox jumps".split()
    s2 = "the kwik brwn focks jumpd".split()

    print("Input 1:", s1)
    print("Input 2:", s2)

    # Standard LCS
    len_std, lcs_std = lcs(s1, s2)
    print("\nStandard LCS:")
    print("Length:", len_std)
    print("LCS:", lcs_std)

    # 1-gram LCS with tolerance
    tolerance = 2
    len_tol, lcs_tol = lcs_1gram(s1, s2, tolerance=tolerance)
    print(f"\n1-gram LCS with tolerance = {tolerance}:")
    print("Length:", len_tol)
    print("LCS:", lcs_tol)
