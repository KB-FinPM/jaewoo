from dataclasses import dataclass


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_calls: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


token_usage = TokenUsage()


def add_usage(input_tokens: int = 0, output_tokens: int = 0):
    token_usage.input_tokens += input_tokens or 0
    token_usage.output_tokens += output_tokens or 0
    token_usage.total_calls += 1


def get_usage() -> TokenUsage:
    return token_usage


def print_usage_summary():
    usage = get_usage()

    print("")
    print("[Token Usage Summary]")
    print(f"- Bedrock calls : {usage.total_calls}")
    print(f"- Input tokens  : {usage.input_tokens:,}")
    print(f"- Output tokens : {usage.output_tokens:,}")
    print(f"- Total tokens  : {usage.total_tokens:,}")
