"""
Синтаксический анализатор для грамматики объявления комплексных чисел в Rust-подобном синтаксисе.
Реализует рекурсивный спуск с нейтрализацией ошибок методом Айронса.
"""
from dataclasses import dataclass
from typing import List, Optional
from .analyzer import Token, TokenType


@dataclass
class SyntaxError:
    """Ошибка синтаксического анализа."""
    line: int
    column: int
    message: str
    fragment: str  # неверный фрагмент (лексема или символ)


class SyntaxAnalyzer:
    def __init__(self, tokens: List[Token]):
        # Фильтруем пробелы и ошибки лексического анализа (но сохраняем позиции)
        self.tokens = [t for t in tokens if t.type not in (TokenType.WHITESPACE, TokenType.ERROR)]
        self.errors: List[SyntaxError] = []
        self.pos = 0  # текущий индекс в self.tokens
        self.sync_tokens = {
            TokenType.END_OF_STATEMENT,   # ;
            TokenType.KEYWORD,            # let
            TokenType.SEPARATOR,          # ( ) ,
        }

    def analyze(self) -> List[SyntaxError]:
        """Запуск синтаксического анализа. Возвращает список ошибок."""
        self.errors.clear()
        self.pos = 0
        
        # Ожидаем одно или несколько объявлений (statement)
        while self.pos < len(self.tokens):
            self.statement()
            # После каждого statement должен быть END_OF_STATEMENT (;)
            # Если его нет, ошибка будет обнаружена внутри statement
        return self.errors

    # ========== Вспомогательные методы ==========

    def current_token(self) -> Optional[Token]:
        """Текущий токен или None если конец."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def peek(self, offset=0) -> Optional[Token]:
        """Токен на позиции pos + offset."""
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return None

    def match(self, expected_type: TokenType, lexeme: Optional[str] = None) -> bool:
        """
        Проверяет, соответствует ли текущий токен ожидаемому типу (и лексеме).
        Если да, продвигает pos и возвращает True.
        """
        token = self.current_token()
        if token and token.type == expected_type:
            if lexeme is not None and token.lexeme != lexeme:
                return False
            self.pos += 1
            return True
        return False

    def consume(self, expected_type: TokenType, lexeme: Optional[str] = None, error_msg: str = "") -> bool:
        """
        Пытается сопоставить токен. Если не удается, добавляет ошибку и пытается
        синхронизироваться (пропустить токены до синхронизирующего).
        Возвращает True, если токен успешно потреблен.
        """
        if self.match(expected_type, lexeme):
            return True
        
        # Ошибка: ожидался другой токен
        token = self.current_token()
        if token:
            fragment = token.lexeme
            line = token.start_line
            col = token.start_col
        else:
            fragment = "конец файла"
            line = self.tokens[-1].end_line if self.tokens else 1
            col = self.tokens[-1].end_col if self.tokens else 1
        
        if not error_msg:
            expected = f"'{lexeme}'" if lexeme else expected_type.name
            error_msg = f"Ожидается {expected}, но получено '{fragment}'"
        
        self.errors.append(SyntaxError(line, col, error_msg, fragment))
        
        # Синхронизация: пропускаем токены до синхронизирующего
        self.synchronize()
        return False

    def synchronize(self):
        """Пропускает токены до достижения синхронизирующего токена, затем пропускает и его."""
        while self.current_token() and self.current_token().type not in self.sync_tokens:
            self.pos += 1
        # Пропускаем синхронизирующий токен тоже
        if self.current_token():
            self.pos += 1

    # ========== Правила грамматики ==========

    def statement(self):
        """<statement> → KEYWORD IDENTIFIER OPERATOR expression END_OF_STATEMENT"""
        # KEYWORD 'let'
        if not self.consume(TokenType.KEYWORD, "let", "Ожидается ключевое слово 'let'"):
            return
        
        # IDENTIFIER
        if not self.consume(TokenType.IDENTIFIER, None, "Ожидается идентификатор после 'let'"):
            return
        
        # OPERATOR '='
        if not self.consume(TokenType.OPERATOR, "=", "Ожидается оператор '=' после идентификатора"):
            return
        
        # expression
        self.expression()
        
        # END_OF_STATEMENT ';'
        self.consume(TokenType.END_OF_STATEMENT, ";", "Ожидается ';' в конце оператора")

    def expression(self):
        """<expression> → path SEPARATOR '(' arguments SEPARATOR ')'"""
        # path (включая все сегменты, например num::complex::Complex::new)
        self.path()
        
        # SEPARATOR '('
        if not self.consume(TokenType.SEPARATOR, "(", "Ожидается '(' после пути"):
            return
        
        # arguments
        self.arguments()
        
        # SEPARATOR ')'
        self.consume(TokenType.SEPARATOR, ")", "Ожидается ')' после аргументов")

    def path(self):
        """<path> → IDENTIFIER (COLON COLON IDENTIFIER)*"""
        # Первый идентификатор обязателен
        if not self.consume(TokenType.IDENTIFIER, None, "Ожидается идентификатор в пути"):
            return
        
        # Повторяем пары COLON COLON IDENTIFIER
        while self.peek() and self.peek().type == TokenType.COLON:
            # Пропускаем два двоеточия
            self.pos += 1
            if not self.match(TokenType.COLON):
                # Если только одно двоеточие, ошибка
                token = self.current_token()
                if token:
                    self.errors.append(SyntaxError(
                        token.start_line, token.start_col,
                        "Ожидается второе ':' для оператора '::'",
                        token.lexeme
                    ))
                break
            # После '::' должен быть идентификатор
            if not self.consume(TokenType.IDENTIFIER, None, "Ожидается идентификатор после '::'"):
                break

    def arguments(self):
        """<arguments> → number (SEPARATOR ',' number)*"""
        if not self.number():
            # Если нет числа, это ошибка, но возможно пустой список аргументов?
            # В нашей грамматике аргументы должны быть хотя бы одно число.
            token = self.current_token()
            if token:
                self.errors.append(SyntaxError(
                    token.start_line, token.start_col,
                    "Ожидается число в качестве аргумента",
                    token.lexeme
                ))
            return
        
        # Дополнительные аргументы через запятую
        while self.peek() and self.peek().type == TokenType.SEPARATOR and self.peek().lexeme == ",":
            self.pos += 1  # пропускаем ','
            self.number()  # следующее число (может быть ошибка)

    def number(self) -> bool:
        """<number> → INTEGER | FLOAT | OPERATOR '-' FLOAT | OPERATOR '-' INTEGER"""
        # Проверяем наличие унарного минуса
        if self.match(TokenType.OPERATOR, "-"):
            # После минуса должно быть число
            if self.match(TokenType.FLOAT) or self.match(TokenType.INTEGER):
                return True
            else:
                # Ошибка: после минуса нет числа
                token = self.current_token()
                if token:
                    self.errors.append(SyntaxError(
                        token.start_line, token.start_col,
                        "Ожидается число после '-'",
                        token.lexeme
                    ))
                return False
        else:
            # Без знака
            return self.match(TokenType.FLOAT) or self.match(TokenType.INTEGER)


def parse_syntax(tokens: List[Token]) -> List[SyntaxError]:
    """Публичная функция для синтаксического анализа."""
    analyzer = SyntaxAnalyzer(tokens)
    return analyzer.analyze()