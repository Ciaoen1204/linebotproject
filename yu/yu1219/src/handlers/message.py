class MessageHandler:
    def __init__(self, generative_ai):
        self.generative_ai = generative_ai

    def handle_message(self, message):
        response_text = self.generative_ai.generate_response(message)
        return response_text