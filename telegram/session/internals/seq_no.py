class SeqNo:
    def __init__(self):
        self.content_related_messages_sent = 0

    def __call__(self, is_content_related: bool) -> int:
        seq_no = (self.content_related_messages_sent * 2) + (1 if is_content_related else 0)

        if is_content_related:
            self.content_related_messages_sent += 1

        return seq_no
