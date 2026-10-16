import unittest

from fastapi.testclient import TestClient

from main import create_app


class CorsMiddlewareTests(unittest.TestCase):
    def test_allowed_origin_can_make_api_preflight_request(self) -> None:
        client = TestClient(create_app(["https://cfo.example.com"]))

        response = client.options(
            "/api/agent_cfo",
            headers={
                "Origin": "https://cfo.example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "https://cfo.example.com",
        )
        self.assertNotIn("access-control-allow-credentials", response.headers)
        self.assertIn("POST", response.headers["access-control-allow-methods"])

    def test_unlisted_origin_is_rejected(self) -> None:
        client = TestClient(create_app(["https://cfo.example.com"]))

        response = client.options(
            "/api/agent_cfo",
            headers={
                "Origin": "https://attacker.example",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_disallowed_method_is_rejected(self) -> None:
        client = TestClient(create_app(["https://cfo.example.com"]))

        response = client.options(
            "/api/agent_cfo",
            headers={
                "Origin": "https://cfo.example.com",
                "Access-Control-Request-Method": "DELETE",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(
            "DELETE",
            response.headers["access-control-allow-methods"],
        )


if __name__ == "__main__":
    unittest.main()
