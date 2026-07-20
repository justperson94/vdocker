from vdocker.formatters.info import mask_env


class TestMaskEnv:
    def test_plain_value_kept(self):
        assert mask_env(["POSTGRES_DB=mydb"]) == [("POSTGRES_DB", "mydb")]

    def test_password_masked(self):
        assert mask_env(["POSTGRES_PASSWORD=hunter2"]) == [
            ("POSTGRES_PASSWORD", "********")]

    def test_secret_and_token_masked(self):
        result = dict(mask_env(["JWT_SECRET=abc", "API_TOKEN=def", "PORT=80"]))
        assert result["JWT_SECRET"] == "********"
        assert result["API_TOKEN"] == "********"
        assert result["PORT"] == "80"

    def test_case_insensitive(self):
        assert mask_env(["db_password=x"]) == [("db_password", "********")]

    def test_value_containing_equals(self):
        assert mask_env(["OPTS=a=b=c"]) == [("OPTS", "a=b=c")]

    def test_no_equals_sign(self):
        # a bare string without '=' should not crash or be masked
        assert mask_env(["JUSTAKEY"]) == [("JUSTAKEY", "")]
