Expression
==========

Arithmetic Expression Representation
------------------------------------

.. autoclass:: holon.flows.expression.ExpressionNode

.. autoclass:: holon.flows.expression.NullExpressionNode
.. autoclass:: holon.flows.expression.ValueExpressionNode
.. autoclass:: holon.flows.expression.VariableExpressionNode
.. autoclass:: holon.flows.expression.UnaryExpressionNode
.. autoclass:: holon.flows.expression.BinaryExpressionNode
.. autoclass:: holon.flows.expression.FunctionExpressionNode
.. autoclass:: holon.flows.expression.ExpressionKind
.. autoclass:: holon.flows.expression.UnboundExpression


Parser and Lexer
----------------

The following classes are internal classes for parsing the arithmetic location.
They are documented here for transparency, potential extension or reuse. It is
very unlikely that the user of the library would need to access them directly.

.. autoclass:: holon.flows.expression.parser.ExpressionParser

.. autoclass:: holon.flows.expression.parser.SyntaxError

.. autoclass:: holon.flows.expression.lexer.Lexer

.. autoclass:: holon.flows.expression.lexer.ParserError

.. autoclass:: holon.flows.expression.lexer.TokenType

.. autoclass:: holon.flows.expression.lexer.TextLocation


