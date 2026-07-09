import os
import re
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

# Set Hugging Face token
os.environ["HF_TOKEN"] = "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"

class VietnameseNERRedactor:
    def __init__(self, confidence_threshold=0.5):
        """
        Initialize Vietnamese NER Redactor using NlpHUST model
        
        Args:
            confidence_threshold (float): Minimum confidence score for entity detection
        """
        self.tokenizer = AutoTokenizer.from_pretrained("NlpHUST/ner-vietnamese-electra-base")
        self.model = AutoModelForTokenClassification.from_pretrained("NlpHUST/ner-vietnamese-electra-base")
        self.nlp = pipeline("ner", model=self.model, tokenizer=self.tokenizer, aggregation_strategy="first")
        self.confidence_threshold = confidence_threshold
        
        # Comprehensive redaction map for all PII types
        self.redaction_map = {
            # NER model entities
            "PERSON": "[TÊN NGƯỜI]",
            "ORGANIZATION": "[TỔ CHỨC]",
            "LOCATION": "[ĐỊA ĐIỂM]",
            
            # PII types
            "PHONE": "[SỐ ĐIỆN THOẠI]",
            "EMAIL": "[EMAIL]",
            "CCCD": "[CCCD/CMND]",
            "DATE": "[NGÀY SINH]",
            "DATEOFBIRTH": "[NGÀY SINH]",
            "CREDIT_CARD": "[THẺ TÍN DỤNG]",
            "BANK_ACCOUNT": "[SỐ TÀI KHOẢN]",
            "BHYT": "[BHYT]",
            "BHXH": "[BHXH]",
            "TAX_CODE": "[MÃ SỐ THUẾ]",
            "EMPLOYEE_ID": "[MÃ SỐ LAO ĐỘNG]",
            "IP_ADDRESS": "[ĐỊA CHỈ IP]",
            "ADDRESS": "[ĐỊA CHỈ]",
            "STREET": "[ĐƯỜNG]",
            "CITY": "[THÀNH PHỐ]",
            "DISTRICT": "[QUẬN/HUYỆN]",
            "WARD": "[PHƯỜNG/XÃ]",
        }
        
    def _merge_entities(self, entities):
        """Merge fragmented entities (B-PERSON, I-PERSON, etc.) into complete entities"""
        merged = []
        i = 0
        
        while i < len(entities):
            entity = entities[i]
            entity_type = entity['entity_group']
            entity_text = entity['word']
            start = entity['start']
            end = entity['end']
            scores = [entity['score']]
            
            # Check if there are more parts to this entity
            j = i + 1
            while j < len(entities) and entities[j]['entity_group'] == entity_type:
                # Check if tokens are consecutive
                if entities[j]['start'] - entities[j-1]['end'] <= 3:
                    entity_text += entities[j]['word']
                    end = entities[j]['end']
                    scores.append(entities[j]['score'])
                    j += 1
                else:
                    break
            
            # Calculate average score
            avg_score = sum(scores) / len(scores) if scores else 0
            
            if avg_score >= self.confidence_threshold:
                merged.append({
                    'entity_group': entity_type,
                    'word': entity_text,
                    'start': start,
                    'end': end,
                    'score': avg_score
                })
            
            i = j
        
        return merged
    
    def _detect_phone_numbers(self, text, entities):
        """Detect Vietnamese phone numbers in various formats"""
        patterns = [
            # +84 format
            r'\+84\s*\d{9,10}',
            r'\+84\s*[0-9]{2,3}[\s.-]?[0-9]{3,4}[\s.-]?[0-9]{3,4}',
            r'\+84\s*\([0-9]{2,3}\)\s*[0-9]{3,4}[\s.-]?[0-9]{3,4}',
            
            # 0 format
            r'0\d{9,10}',
            r'0\d{2,3}[\s.-]\d{3,4}[\s.-]\d{3,4}',
            r'0\d{2,3}\s*[0-9]{3,4}\s*[0-9]{3,4}',
            r'\(0\d{2,3}\)\s*[0-9]{3,4}[\s.-]?[0-9]{3,4}',
            
            # Landline with area code
            r'\(0[0-9]{2,3}\)\s*[0-9]{3,4}[\s.-]?[0-9]{3,4}',
            r'0[0-9]{2,3}\s*[0-9]{3,4}[\s.-]?[0-9]{3,4}',
            
            # International format with country code
            r'\+[0-9]{1,3}\s*[0-9]{2,3}[\s.-]?[0-9]{3,4}[\s.-]?[0-9]{3,4}',
            
            # SĐT or ĐT prefixes
            r'(?:SĐT|ĐT)\s*[:;]\s*[0-9+\s.-]{10,15}',
            r'(?:SĐT|ĐT)\s*[:;]\s*\([0-9]{2,3}\)\s*[0-9]{3,4}[\s.-]?[0-9]{3,4}',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean the matched text
                cleaned = match.group().strip()
                # Check if it's a valid phone number (at least 10 digits)
                digits = re.sub(r'\D', '', cleaned)
                if 9 <= len(digits) <= 15:
                    entities.append({
                        'entity_group': 'PHONE',
                        'word': cleaned,
                        'start': match.start(),
                        'end': match.end(),
                        'score': 1.0
                    })
        
        return entities
    
    def _detect_emails(self, text, entities):
        """Detect email addresses"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.finditer(email_pattern, text)
        for match in matches:
            entities.append({
                'entity_group': 'EMAIL',
                'word': match.group(),
                'start': match.start(),
                'end': match.end(),
                'score': 1.0
            })
        
        return entities
    
    def _detect_cccd(self, text, entities):
        """Detect Vietnamese Citizen ID (CCCD/CMND)"""
        # Various ID formats
        patterns = [
            r'\b0\d{11}\b',  # CCCD 12 digits
            r'\b\d{9}\b',    # CMND 9 digits (old format)
            r'\bCCCD\s*[:;]\s*[0-9]{12}\b',  # CCCD: 012345678901
            r'\bCMND\s*[:;]\s*[0-9]{9}\b',   # CMND: 123456789
            r'\b(?:CCCD|CMND)\s*[:;]\s*[0-9]{9,12}\b',  # General ID
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract just the number
                id_number = re.search(r'\d{9,12}', match.group())
                if id_number:
                    entities.append({
                        'entity_group': 'CCCD',
                        'word': id_number.group(),
                        'start': match.start() + match.group().find(id_number.group()),
                        'end': match.start() + match.group().find(id_number.group()) + len(id_number.group()),
                        'score': 1.0
                    })
        
        return entities
    
    def _detect_bhyt_bhxh(self, text, entities):
        """Detect BHYT (Health insurance) and BHXH (Social insurance) numbers"""
        patterns = [
            # BHYT: 15 digits (format: XX YY ZZZZZZZZZZ)
            r'\bBHYT\s*[:;]\s*[0-9]{15}\b',
            r'\bBHYT\s*[:;]\s*[0-9]{3}\s*[0-9]{3}\s*[0-9]{9}\b',
            r'\bBHYT\s*[:;]\s*[0-9]{3}-[0-9]{3}-[0-9]{9}\b',
            r'\b[0-9]{3}\s*[0-9]{3}\s*[0-9]{9}\b',  # Just the number (15 digits)
            r'\b[0-9]{15}\b',  # Any 15-digit number
            r'\bBHXH\s*[:;]\s*[0-9]{10}\b',  # BHXH: 10 digits
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract the number
                digits = re.search(r'\d+', match.group())
                if digits:
                    num = digits.group()
                    if len(num) == 15:
                        entities.append({
                            'entity_group': 'BHYT',
                            'word': num,
                            'start': match.start() + match.group().find(num),
                            'end': match.start() + match.group().find(num) + len(num),
                            'score': 1.0
                        })
                    elif len(num) == 10:
                        entities.append({
                            'entity_group': 'BHXH',
                            'word': num,
                            'start': match.start() + match.group().find(num),
                            'end': match.start() + match.group().find(num) + len(num),
                            'score': 1.0
                        })
        
        return entities
    
    def _detect_tax_code(self, text, entities):
        """Detect Vietnamese tax code (Mã số thuế)"""
        patterns = [
            r'\bMã số thuế\s*[:;]\s*[0-9]{10}-[0-9]{3}\b',
            r'\bMST\s*[:;]\s*[0-9]{10}-[0-9]{3}\b',
            r'\bMã số thuế\s*[:;]\s*[0-9]{10}\b',
            r'\b[0-9]{10}-[0-9]{3}\b',  # Just the tax code format
            r'\b[0-9]{10}\s*-\s*[0-9]{3}\b',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                tax_code = re.search(r'[0-9]{10}-[0-9]{3}|[0-9]{10}', match.group())
                if tax_code:
                    entities.append({
                        'entity_group': 'TAX_CODE',
                        'word': tax_code.group(),
                        'start': match.start() + match.group().find(tax_code.group()),
                        'end': match.start() + match.group().find(tax_code.group()) + len(tax_code.group()),
                        'score': 1.0
                    })
        
        return entities
    
    def _detect_employee_id(self, text, entities):
        """Detect employee ID (Mã số lao động)"""
        patterns = [
            r'\bMã số lao động\s*[:;]\s*[A-Za-z0-9\-_]+\b',
            r'\bMã NV\s*[:;]\s*[A-Za-z0-9\-_]+\b',
            r'\bEmployee ID\s*[:;]\s*[A-Za-z0-9\-_]+\b',
            r'\bMSLĐ\s*[:;]\s*[A-Za-z0-9\-_]+\b',
            r'\bLAO-\d{4}-\d{3}\b',  # LAO-2024-001 format
            r'\bNV-[A-Za-z0-9\-_]+\b',  # NV-2024-001 format
            r'\bEMP-[A-Za-z0-9\-_]+\b',  # EMP-001 format
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract the ID part
                id_match = re.search(r'[A-Za-z0-9\-_]+$', match.group())
                if id_match:
                    entities.append({
                        'entity_group': 'EMPLOYEE_ID',
                        'word': id_match.group(),
                        'start': match.start() + match.group().find(id_match.group()),
                        'end': match.start() + match.group().find(id_match.group()) + len(id_match.group()),
                        'score': 1.0
                    })
        
        return entities
    
    def _detect_bank_account(self, text, entities):
        """Detect bank account numbers"""
        patterns = [
            r'\bSố tài khoản\s*[:;]\s*[0-9]{8,14}\b',
            r'\bSTK\s*[:;]\s*[0-9]{8,14}\b',
            r'\bAccount\s*[:;]\s*[0-9]{8,14}\b',
            r'\b[0-9]{8,14}\b',  # Generic 8-14 digit number (but avoid phone numbers)
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                digits = re.search(r'[0-9]{8,14}', match.group())
                if digits:
                    num = digits.group()
                    # Skip if it looks like a phone number (10 digits starting with 0)
                    if not (len(num) == 10 and num.startswith('0')):
                        entities.append({
                            'entity_group': 'BANK_ACCOUNT',
                            'word': num,
                            'start': match.start() + match.group().find(num),
                            'end': match.start() + match.group().find(num) + len(num),
                            'score': 1.0
                        })
        
        return entities
    
    def _detect_credit_cards(self, text, entities):
        """Detect credit card numbers"""
        cc_patterns = [
            r'\b4[0-9]{12}(?:[0-9]{3})?\b',  # Visa
            r'\b5[1-5][0-9]{14}\b',          # MasterCard
            r'\b3[47][0-9]{13}\b',           # Amex
            r'\b6(?:011|5[0-9]{2})[0-9]{12}\b',  # Discover
            r'\b(?:[0-9]{4}[\s-]?){3,4}[0-9]{4}\b',  # General: XXXX-XXXX-XXXX-XXXX
            r'\bThẻ tín dụng\s*[:;]\s*[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}\b',
            r'\bThẻ\s*[:;]\s*[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}\b',
        ]
        
        for pattern in cc_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean the number
                cc_num = re.sub(r'[\s-]', '', match.group())
                # Extract just the digits
                digits_only = re.sub(r'\D', '', match.group())
                if 13 <= len(digits_only) <= 19:  # Valid credit card length
                    entities.append({
                        'entity_group': 'CREDIT_CARD',
                        'word': match.group().strip(),
                        'start': match.start(),
                        'end': match.end(),
                        'score': 1.0
                    })
        
        return entities
    
    def _detect_ip_addresses(self, text, entities):
        """Detect IP addresses (IPv4 and IPv6)"""
        # IPv4
        ipv4_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        matches = re.finditer(ipv4_pattern, text)
        for match in matches:
            # Validate IP
            parts = match.group().split('.')
            if all(0 <= int(part) <= 255 for part in parts):
                entities.append({
                    'entity_group': 'IP_ADDRESS',
                    'word': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'score': 1.0
                })
        
        # IPv6 (simplified)
        ipv6_pattern = r'\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b'
        matches = re.finditer(ipv6_pattern, text)
        for match in matches:
            entities.append({
                'entity_group': 'IP_ADDRESS',
                'word': match.group(),
                'start': match.start(),
                'end': match.end(),
                'score': 1.0
            })
        
        return entities
    
    def _detect_addresses(self, text, entities):
        """Detect Vietnamese addresses with city/district/ward"""
        # Street + Ward + District + City patterns
        address_patterns = [
            r'\b[0-9]+(?:\s*[A-Za-zÀ-ỹ\s]+)?\s*(?:đường|đ|phố|ngõ|hẻm|ngách)\s+[A-Za-zÀ-ỹ\s]+',
            r'\b(?:phường|xã|thị trấn)\s+[A-Za-zÀ-ỹ\s]+',
            r'\b(?:quận|huyện|thành phố|tỉnh)\s+[A-Za-zÀ-ỹ\s]+',
            r'\bTP\.?\s*[A-Za-zÀ-ỹ\s]+',
            r'\bT\.?\s*[A-Za-zÀ-ỹ\s]+',
            r'\bQuận\s+[0-9]+',
        ]
        
        for pattern in address_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Check if this is part of a larger entity (avoid duplicates)
                if not self._is_overlapping(match.start(), match.end(), entities):
                    entities.append({
                        'entity_group': 'ADDRESS',
                        'word': match.group().strip(),
                        'start': match.start(),
                        'end': match.end(),
                        'score': 0.8
                    })
        
        return entities
    
    def _is_overlapping(self, start, end, entities):
        """Check if a range overlaps with existing entities"""
        for entity in entities:
            if not (end <= entity['start'] or start >= entity['end']):
                return True
        return False
    
    def _add_common_pii_regex(self, text, entities):
        """Add common PII detection using regex for items not covered by NER model"""
        entities = self._detect_phone_numbers(text, entities)
        entities = self._detect_emails(text, entities)
        entities = self._detect_cccd(text, entities)
        entities = self._detect_bhyt_bhxh(text, entities)
        entities = self._detect_tax_code(text, entities)
        entities = self._detect_employee_id(text, entities)
        entities = self._detect_bank_account(text, entities)
        entities = self._detect_credit_cards(text, entities)
        entities = self._detect_ip_addresses(text, entities)
        entities = self._detect_addresses(text, entities)
        return entities
    
    def _remove_overlapping_entities(self, entities):
        """Remove overlapping entities, keep the one with higher confidence"""
        if not entities:
            return []
        
        # Sort by start position
        sorted_entities = sorted(entities, key=lambda x: (x['start'], -x['end']))
        
        unique_entities = []
        for entity in sorted_entities:
            overlap = False
            for added in unique_entities:
                if not (entity['end'] <= added['start'] or entity['start'] >= added['end']):
                    overlap = True
                    if entity['score'] > added['score']:
                        unique_entities.remove(added)
                        unique_entities.append(entity)
                    break
            
            if not overlap:
                unique_entities.append(entity)
        
        return unique_entities
    
    def _detect_dates(self, text, entities):
        """Detect dates in various formats"""
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',  # DD/MM/YYYY, DD-MM-YYYY
            r'\b\d{1,2}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{4}\b',  # With spaces
            r'\b(?:ngày|sinh)\s+\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',  # With prefix
            r'\b\d{1,2}\s*(?:tháng|/)\s*\d{1,2}\s*(?:năm|/)\s*\d{4}\b',  # Vietnamese words
            r'\b\d{4}-\d{1,2}-\d{1,2}\b',  # YYYY-MM-DD
        ]
        
        for pattern in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract the date part
                date_match = re.search(r'\d{1,2}[\s/-]+\d{1,2}[\s/-]+\d{4}', match.group())
                if date_match:
                    entities.append({
                        'entity_group': 'DATE',
                        'word': date_match.group(),
                        'start': match.start() + match.group().find(date_match.group()),
                        'end': match.start() + match.group().find(date_match.group()) + len(date_match.group()),
                        'score': 1.0
                    })
        
        return entities
    
    def analyze(self, text):
        """Analyze text and return detected entities"""
        # Get NER results
        ner_results = self.nlp(text)
        
        # Merge entities
        merged_entities = self._merge_entities(ner_results)
        
        # Add date detection
        date_entities = self._detect_dates(text, [])
        all_entities = merged_entities + date_entities
        
        # Add regex-based PII detection
        all_entities = self._add_common_pii_regex(text, all_entities)
        
        # Remove overlaps
        unique_entities = self._remove_overlapping_entities(all_entities)
        
        # Group by type
        grouped = {}
        for entity in unique_entities:
            e_type = entity['entity_group']
            if e_type not in grouped:
                grouped[e_type] = []
            grouped[e_type].append({
                'text': entity['word'],
                'score': entity['score'],
                'position': (entity['start'], entity['end'])
            })
        
        return grouped
    
    def redact(self, text):
        """Redact PII from text"""
        # Get NER results
        ner_results = self.nlp(text)
        
        # Merge entities
        merged_entities = self._merge_entities(ner_results)
        
        # Add date detection
        date_entities = self._detect_dates(text, [])
        all_entities = merged_entities + date_entities
        
        # Add regex-based PII detection
        all_entities = self._add_common_pii_regex(text, all_entities)
        
        # Remove overlaps
        unique_entities = self._remove_overlapping_entities(all_entities)
        
        # Sort by start position in reverse order for safe replacement
        unique_entities = sorted(unique_entities, key=lambda x: x['start'], reverse=True)
        
        redacted = text
        for entity in unique_entities:
            entity_type = entity['entity_group']
            replacement = self.redaction_map.get(entity_type, f"[{entity_type}]")
            
            # Replace the exact text
            redacted = redacted[:entity['start']] + replacement + redacted[entity['end']:]
        
        return redacted
    
    def redact_with_report(self, text):
        """Redact PII and return both redacted text and analysis report"""
        # Get NER results
        ner_results = self.nlp(text)
        
        # Merge entities
        merged_entities = self._merge_entities(ner_results)
        
        # Add date detection
        date_entities = self._detect_dates(text, [])
        all_entities = merged_entities + date_entities
        
        # Add regex-based PII detection
        all_entities = self._add_common_pii_regex(text, all_entities)
        
        # Remove overlaps
        unique_entities = self._remove_overlapping_entities(all_entities)
        
        # Generate report
        report = {
            'total_entities': len(unique_entities),
            'entities_by_type': {},
            'redacted_terms': []
        }
        
        for entity in unique_entities:
            e_type = entity['entity_group']
            if e_type not in report['entities_by_type']:
                report['entities_by_type'][e_type] = 0
            report['entities_by_type'][e_type] += 1
            report['redacted_terms'].append({
                'type': e_type,
                'text': entity['word'],
                'confidence': entity['score']
            })
        
        # Redact
        unique_entities_sorted = sorted(unique_entities, key=lambda x: x['start'], reverse=True)
        redacted = text
        for entity in unique_entities_sorted:
            entity_type = entity['entity_group']
            replacement = self.redaction_map.get(entity_type, f"[{entity_type}]")
            redacted = redacted[:entity['start']] + replacement + redacted[entity['end']:]
        
        return redacted, report


# ============ MAIN USAGE ============

def main():
    # Initialize redactor
    redactor = VietnameseNERRedactor(confidence_threshold=0.5)
    
    # Test text with all PII types
    test_text = """
Hồ sơ nhân sự của ông Nguyễn Văn Đức (CCCD: 012345678901, sinh: 22/11/1983):
- Địa chỉ: 345 Bà Triệu, Q. Hai Bà Trưng, Hà Nội
- SĐT: +84 982 345 678
- Email: duc.nguyen@company.net
- Tài khoản ngân hàng: 4567890123 tại VietinBank
- Thẻ tín dụng: 5555-6666-7777-8888
- IP công ty: 192.168.1.50
- BHYT: 1234567890123456
- Số thuế: 1234567890-123
- Mã số lao động: LAO-2024-001
"""

    print("=" * 70)
    print("VIETNAMESE PII REDACTOR - COMPLETE VERSION")
    print("=" * 70)
    
    # Analyze
    print("\n📊 ENTITY ANALYSIS")
    print("-" * 70)
    entities = redactor.analyze(test_text)
    for entity_type, instances in entities.items():
        print(f"  {entity_type:15}:")
        for inst in instances:
            print(f"      - {inst['text']:30} (score: {inst['score']:.3f})")
    
    # Redact
    print("\n🔒 REDACTED TEXT")
    print("-" * 70)
    redacted_text = redactor.redact(test_text)
    print(redacted_text)
    
    # Redact with report
    print("\n📋 REDACTION REPORT")
    print("-" * 70)
    redacted, report = redactor.redact_with_report(test_text)
    print(f"Total entities redacted: {report['total_entities']}")
    print("Entities by type:")
    for e_type, count in report['entities_by_type'].items():
        print(f"  - {e_type}: {count}")
    
    print("\nRedacted terms:")
    for term in report['redacted_terms']:
        print(f"  - {term['type']}: '{term['text']}' (conf: {term['confidence']:.3f})")
    
    # Compare original vs redacted
    print("\n📝 ORIGINAL VS REDACTED COMPARISON")
    print("-" * 70)
    print("\n🔴 ORIGINAL:")
    print(test_text.strip())
    print("\n✅ REDACTED:")
    print(redacted)


if __name__ == "__main__":
    main()