import unittest
from ml_kem import ML_KEM128, ML_KEM192, ML_KEM256
from drbg.aes256_ctr_drbg import AES256_CTR_DRBG


def read_kat_data(file_name):
    data_blocks = []
    with open(file_name) as f:
        for _ in range(1000):
            data_blocks.append("".join([next(f) for _ in range(11)]))
    return data_blocks


def parse_kat_data(data_blocks):
    parsed_data = {}
    for block in data_blocks:
        block_data = block.split("\n")[:-1]
        count, z, d, msg, seed, pk, sk, ct_n, ss_n, ct, ss = [
            line.split(" = ")[-1] for line in block_data
        ]
        parsed_data[int(count)] = {
            "z": bytes.fromhex(z),
            "d": bytes.fromhex(d),
            "msg": bytes.fromhex(msg),
            "seed": bytes.fromhex(seed),
            "pk": bytes.fromhex(pk),
            "sk": bytes.fromhex(sk),
            "ct_n": bytes.fromhex(ct_n),
            "ss_n": bytes.fromhex(ss_n),
            "ct": bytes.fromhex(ct),
            "ss": bytes.fromhex(ss),
        }
    return parsed_data


class TestML_KEM(unittest.TestCase):
    """
    Test ML_KEM levels for internal
    consistency by generating key pairs
    and shared secrets.
    """

    def generic_test_ML_KEM(self, ML_KEM, count):
        for _ in range(count):
            (ek, dk) = ML_KEM.keygen()
            for _ in range(count):
                (K, c) = ML_KEM.encaps(ek)
                K_prime = ML_KEM.decaps(c, dk)
                self.assertEqual(K, K_prime)

    def test_ML_KEM128(self):
        self.generic_test_ML_KEM(ML_KEM128, 5)

    def test_ML_KEM192(self):
        self.generic_test_ML_KEM(ML_KEM192, 5)

    def test_ML_KEM256(self):
        self.generic_test_ML_KEM(ML_KEM256, 5)


class TestKnownTestValues(unittest.TestCase):
    def generic_test_mlkem_known_answer(self, ML_KEM, filename):
        # Set DRBG to generate seeds
        # https://github.com/post-quantum-cryptography/KAT/tree/main/MLKEM
        entropy_input = bytes.fromhex(
            "60496cd0a12512800a79161189b055ac3996ad24e578d3c5fc57c1e60fa2eb4e550d08e51e9db7b67f1a616681d9182d"
        )
        rng = AES256_CTR_DRBG(entropy_input)

        # Parse the KAT file data
        kat_data_blocks = read_kat_data(filename)
        parsed_data = parse_kat_data(kat_data_blocks)

        # Only test the first 100 for now, running all 1000 is overkill
        # for us as it's pretty slow (~165 seconds)
        for count in range(100):
            # Obtain the kat data for the count
            data = parsed_data[count]

            # Set the seed and check it matches the KAT
            seed = rng.random_bytes(48)
            self.assertEqual(seed, data["seed"])

            # Check that the three chunks of 32 random bytes match
            ML_KEM.set_drbg_seed(seed)

            z = ML_KEM.random_bytes(32)
            d = ML_KEM.random_bytes(32)
            msg = ML_KEM.random_bytes(32)
            self.assertEqual(z, data["z"])
            self.assertEqual(d, data["d"])
            self.assertEqual(msg, data["msg"])

            # Reset the seed
            ML_KEM.set_drbg_seed(seed)

            # Assert keygen matches
            ek, dk = ML_KEM.keygen()
            self.assertEqual(ek, data["pk"])
            self.assertEqual(dk, data["sk"])

            # Assert encapsulation matches
            K, c = ML_KEM.encaps(ek)
            self.assertEqual(K, data["ss"])
            self.assertEqual(c, data["ct"])

            # Assert decapsulation matches
            _K = ML_KEM.decaps(c, dk)
            self.assertEqual(_K, data["ss"])

            # Assert decapsulation with faulty ciphertext
            ss_n = ML_KEM.decaps(data["ct_n"], dk)
            self.assertEqual(ss_n, data["ss_n"])

    def test_mlkem_512_known_answer(self):
        return self.generic_test_mlkem_known_answer(
            ML_KEM128, "assets/kat_MLKEM_512.rsp"
        )

    def test_mlkem_768_known_answer(self):
        return self.generic_test_mlkem_known_answer(
            ML_KEM192, "assets/kat_MLKEM_768.rsp"
        )

    def test_mlkem_1024_known_answer(self):
        return self.generic_test_mlkem_known_answer(
            ML_KEM256, "assets/kat_MLKEM_1024.rsp"
        )


if __name__ == "__main__":
    unittest.main()
