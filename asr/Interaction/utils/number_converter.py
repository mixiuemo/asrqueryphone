import re
from utils.phone_location import PhoneLocation

class NumberConverter:
 
    CN_NUM = {
        '零': '0',
        '一': '1',
        '二': '2',
        '三': '3',
        '四': '4',
        '五': '5',
        '六': '6',
        '七': '7',
        '八': '8',
        '九': '9',
        '幺': '1',
        '两': '2',
        '俩': '2',
        '拐': '7',
        '勾': '9',
    }
    
    @staticmethod
    def extract_continuous_numbers(text: str) -> list:
        if not text:
            return []
            
        result = text
        for cn, ar in NumberConverter.CN_NUM.items():
            result = result.replace(cn, ar)
            
        numbers = re.findall(r'\d+', result)
        
        valid_numbers = [num for num in numbers if len(num) in PhoneLocation.DIRECT_DIAL_LENGTHS]
        
        return valid_numbers

    @staticmethod
    def has_valid_phone_number(text: str) -> tuple:
        numbers = NumberConverter.extract_continuous_numbers(text)
        return (bool(numbers), numbers[0] if numbers else None) 
