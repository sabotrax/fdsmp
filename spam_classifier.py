import os
import json
from langchain_ollama import OllamaLLM
from langchain.prompts import FewShotPromptTemplate, PromptTemplate
from dotenv import load_dotenv
import logging

load_dotenv()

class SpamClassifier:
    def __init__(self):
        self.ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model_name = os.getenv('OLLAMA_MODEL', 'llama3.1')
        self.examples_file = os.getenv('SPAM_EXAMPLES_FILE', 'spam_examples.json')
        
        self.llm = OllamaLLM(
            base_url=self.ollama_base_url,
            model=self.model_name
        )
        
        self.spam_examples = self._load_examples()
        self._setup_prompts()
        
    def _load_examples(self):
        """Load spam examples from JSON file"""
        try:
            with open(self.examples_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Validate JSON structure
            if not isinstance(data, dict):
                raise ValueError("JSON must be an object/dict")
            
            if 'examples' not in data:
                raise ValueError("JSON must contain 'examples' key")
            
            examples = data['examples']
            if not isinstance(examples, list):
                raise ValueError("'examples' must be a list")
            
            # Validate each example
            for i, example in enumerate(examples):
                if not isinstance(example, dict):
                    raise ValueError(f"Example {i} must be an object/dict")
                
                if 'email' not in example:
                    raise ValueError(f"Example {i} missing 'email' field")
                
                if 'classification' not in example:
                    raise ValueError(f"Example {i} missing 'classification' field")
                
                if example['classification'] not in ['spam', 'not spam']:
                    raise ValueError(f"Example {i} classification must be 'spam' or 'not spam'")
            
            logging.info(f"Loaded and validated {len(examples)} examples from {self.examples_file}")
            return examples
            
        except FileNotFoundError:
            logging.error(f"Examples file {self.examples_file} not found")
            raise SystemExit(f"FATAL: Examples file {self.examples_file} not found")
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in {self.examples_file}: {e}")
            raise SystemExit(f"FATAL: Invalid JSON in {self.examples_file}: {e}")
        except ValueError as e:
            logging.error(f"Invalid examples format in {self.examples_file}: {e}")
            raise SystemExit(f"FATAL: Invalid examples format in {self.examples_file}: {e}")
        except Exception as e:
            logging.error(f"Failed to load examples from {self.examples_file}: {e}")
            raise SystemExit(f"FATAL: Failed to load examples: {e}")
    
    def _setup_prompts(self):
        """Setup LangChain prompts with loaded examples"""
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
            logging.error(f"FATAL: Failed to classify email with LLM: {e}")
            raise SystemExit(f"FATAL: LLM classification failed: {e}")