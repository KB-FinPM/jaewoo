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


def print_usage_summary(log_func=print):
    log_func('[Token Usage Summary]')
    log_func(f'- Bedrock calls : {token_usage.total_calls}')
    log_func(f'- Input tokens  : {token_usage.input_tokens:,}')
    log_func(f'- Output tokens : {token_usage.output_tokens:,}')
    log_func(f'- Total tokens  : {token_usage.total_tokens:,}')
