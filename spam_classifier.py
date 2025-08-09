import os
import json
import time
from langchain_ollama import OllamaLLM
from langchain.prompts import FewShotPromptTemplate, PromptTemplate
from dotenv import load_dotenv
import logging

load_dotenv()

class SpamClassifier:
    def __init__(self, debug=False, debug_prompt=False):
        self.debug = debug
        self.debug_prompt = debug_prompt
        
        # Enable LangChain debugging only in debug mode
        if debug:
            logging.getLogger("langchain").setLevel(logging.DEBUG)
            logging.getLogger("langchain_ollama").setLevel(logging.DEBUG)
        else:
            # Suppress HTTP requests from LangChain when not in debug mode
            logging.getLogger("langchain").setLevel(logging.WARNING)
            logging.getLogger("langchain_ollama").setLevel(logging.WARNING)
            logging.getLogger("httpx").setLevel(logging.WARNING)
        
        self.ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model_name = os.getenv('OLLAMA_MODEL', 'llama3.1')
        self.examples_file = os.getenv('SPAM_EXAMPLES_FILE', 'spam_examples.json')
        self.temperature = float(os.getenv('LLM_TEMPERATURE', '0.2'))
        self.num_ctx = int(os.getenv('LLM_NUM_CTX', '8192'))
        
        self.llm = OllamaLLM(
            base_url=self.ollama_base_url,
            model=self.model_name,
            temperature=self.temperature,
            num_ctx=self.num_ctx
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
                
                if example['classification'] not in ['typ 1', 'typ 2']:
                    raise ValueError(f"Example {i} classification must be 'typ 1' or 'typ 2'")
            
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
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters for most models)"""
        return len(text) // 4
    
    def _setup_prompts(self):
        """Setup LangChain prompts with loaded examples"""
        self.example_template = PromptTemplate(
            input_variables=["email", "classification"],
            template="Email:\n{email}\n\nClassification: {classification}"
        )
        
        self.prompt = FewShotPromptTemplate(
            examples=self.spam_examples,
            example_prompt=self.example_template,
            prefix="Classify as 'typ 1', 'typ 2', or 'unsure' based on these examples. Pay special attention to examples from the exact same email address. Respond with EXACTLY one word only:",
            suffix="Email:\n{email}\n\nClassification:",
            input_variables=["email"]
        )
        
        # Calculate base prompt size (without actual email)
        sample_prompt = self.prompt.format(email="")
        self.base_prompt_tokens = self._estimate_tokens(sample_prompt)
        
        logging.info(f"Loaded and validated {len(self.spam_examples)} examples from {self.examples_file}")
        logging.info(f"Using LLM model: {self.model_name}")
        logging.info(f"Base prompt size: ~{self.base_prompt_tokens} tokens")
    
    def classify_email(self, email_text: str) -> tuple[str, float]:
        try:
            start_time = time.time()
            if self.debug:
                logging.info("Starting email classification...")
                logging.info(f"Email text length: {len(email_text)} characters")
                
            if self.debug_prompt:
                formatted_prompt = self.prompt.format(email=email_text)
                logging.info(f"Formatted prompt length: {len(formatted_prompt)} characters")
                logging.info(f"Full prompt:\n{formatted_prompt}")
                
            # Use LangChain LLM with FewShotPromptTemplate
            response = self.llm.invoke(self.prompt.format(email=email_text))
            
            if self.debug:
                # Show first and last 50 characters of LLM response
                if len(response) <= 100:
                    logging.info(f"Received LLM response: '{response}'")
                else:
                    first_50 = response[:50]
                    last_50 = response[-50:]
                    logging.info(f"Received LLM response: '{first_50}...{last_50}'")
            
            # Search for classification at end of response using regex
            import re
            stripped = response.lower().strip()
            match = re.search(r'(typ\s+[12]|unsure)$', stripped, re.IGNORECASE)
            
            if match:
                found = match.group(1)
                if "typ 2" in found:
                    result = "spam"
                    classification_found = found
                else:  # typ 1 or unsure
                    result = "not spam"
                    classification_found = found
            else:
                # Fallback: assume not spam if unclear
                if self.debug:
                    logging.warning(f"LLM gave unclear response, assuming not spam: {response[:100]}...")
                result = "not spam"
                classification_found = "fallback"
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            if self.debug:
                logging.info(f"Email classified as: {result} (raw: {classification_found})")
            else:
                if result == "spam":
                    logging.info(f"❌ Email classified as: {result}")
                else:
                    logging.info(f"✅ Email classified as: {result}")
            return result, processing_time
            
        except Exception as e:
            logging.error(f"FATAL: Failed to classify email with LLM: {e}")
            raise SystemExit(f"FATAL: LLM classification failed: {e}")
