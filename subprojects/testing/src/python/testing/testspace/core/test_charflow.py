from unittest import TestCase

from gammaparsing4py.core.charflow import CharFlow


class Test_CharFlow(TestCase):

    def test_basic(self):
        flow: CharFlow = CharFlow.fromString("abcdefghiabc")

        self.assertEqual(flow.peek(), ord("a"))
        self.assertEqual(flow.peek(), ord("a"))
        self.assertEqual(flow.peek(), ord("a"))
        self.assertTrue(flow.hasMore())

        self.assertFalse(flow.check(ord("b")))
        self.assertTrue(flow.hasMore())
        self.assertTrue(flow.check(ord("a")))

        self.assertEqual(flow.peek(), ord("b"))
        self.assertTrue(flow.hasMore())
        flow.read(ord("b"))
        flow.read(ord("c"))
        flow.next()
        flow.next()

        self.assertTrue(flow.hasMore())
        self.assertEqual(flow.peek(), ord("f"))
        self.assertTrue(flow.hasMore())
        self.assertTrue(flow.check(ord("f")))
        self.assertTrue(flow.hasMore())

        flow.next()
        flow.next()
        flow.next()
        self.assertTrue(flow.hasMore())
        flow.next()
        flow.next()
        flow.next()

        self.assertFalse(flow.hasMore())
