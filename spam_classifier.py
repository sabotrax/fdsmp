import os
from langchain_ollama import OllamaLLM
from langchain.prompts import FewShotPromptTemplate, PromptTemplate
from dotenv import load_dotenv
import logging

load_dotenv()

class SpamClassifier:
    def __init__(self):
        self.ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model_name = os.getenv('OLLAMA_MODEL', 'llama3.1')
        
        self.llm = OllamaLLM(
            base_url=self.ollama_base_url,
            model=self.model_name
        )
        
        self.spam_examples = [
            {
                "email": """Subject: URGENT: Claim Your $1000 Prize NOW!
From: winner@prize-claim.com
Content: Congratulations! You've won $1000! Click here immediately to claim your prize before it expires in 24 hours! No purchase necessary! Act now!""",
                "classification": "spam"
            },
            {
                "email": """Subject: Get Rich Quick - Make $5000 a Day Working From Home!
From: easymoney@workfromhome.biz
Content: Make thousands of dollars daily from home! No experience required! Limited time offer! Send us your bank details to get started today!""",
                "classification": "spam"
            },
            {
                "email": """Subject: Your Account Has Been Suspended - Verify Now
From: security@bank-verify.net
Content: Dear customer, your account has been suspended due to suspicious activity. Click this link to verify your identity and avoid permanent suspension. Enter your login credentials immediately.""",
                "classification": "spam"
            },
            {
                "email": """Subject: Meeting Tomorrow at 2 PM
From: colleague@company.com
Content: Hi, just confirming our meeting tomorrow at 2 PM in conference room B. Please bring the quarterly reports we discussed. Thanks!""",
                "classification": "not spam"
            },
            {
                "email": """Subject: Monthly Newsletter - Tech Updates
From: newsletter@techcompany.com
Content: Here are this month's latest updates from our development team. We've released new features and fixed several bugs based on user feedback.""",
                "classification": "not spam"
            }
        ]
        
        self.example_template = PromptTemplate(
            input_variables=["email", "classification"],
            template="Email:\n{email}\n\nClassification: {classification}"
        )
        
        self.prompt = FewShotPromptTemplate(
            examples=self.spam_examples,
            example_prompt=self.example_template,
            prefix="You are an expert email spam classifier. Based on the following examples, classify emails as 'spam' or 'not spam'. Look for indicators like suspicious URLs, urgent language, requests for personal information, get-rich-quick schemes, and phishing attempts.\n\nExamples:",
            suffix="Email:\n{email}\n\nClassification:",
            input_variables=["email"]
        )
    
    def classify_email(self, email_text: str) -> str:
        try:
            formatted_prompt = self.prompt.format(email=email_text)
            
            response = self.llm.invoke(formatted_prompt)
            
            classification = response.strip().lower()
            
            if "spam" in classification and "not spam" not in classification:
                result = "spam"
            else:
                result = "not spam"
            
            logging.info(f"Email classified as: {result}")
            return result
            
        except Exception as e:
            logging.error(f"Failed to classify email: {e}")
            return "not spam"