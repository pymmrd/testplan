"""Test Multitest - Test Suite - Result - Test Report - Exporter integration"""
import re

from testplan.testing.multitest import MultiTest, testsuite, testcase

from testplan.common.utils import comparison as cmp


def always_true(obj):
    return True


@testsuite
class MySuite(object):

    @testcase
    def test_log(self, env, result):
        result.log('hello world')

    @testcase
    def test_comparison(self, env, result):
        result.equal(1, 1, 'equality description')
        result.not_equal(1, 2)
        result.less(1, 2)
        result.greater(2, 1)
        result.less_equal(1, 2)
        result.greater_equal(2, 1)

    @testcase
    def test_approximate_equality(self, env, result):
        result.isclose(95, 100, 0, 5)

    @testcase
    def test_membership(self, env, result):
        result.contain(1, [1, 2, 3])
        result.not_contain('foo', 'bar')

    @testcase
    def test_regex(self, env, result):
        result.regex.match('foo', 'foobar')
        result.regex.not_match('foo', 'bar')

    @testcase
    def test_group_assertions(self, env, result):
        result.equal('foo', 'foo')

        with result.group('assertion group description') as my_group:
            my_group.equal(1, 1)
            my_group.regex.match('hello', 'hello world')

            with my_group.group('sub group description') as sub_group:
                sub_group.equal('foo', 'foo')

    @testcase
    def test_summary_assertions(self, env, result):
        with result.group(summarize=True, num_passing=2) as group:
            for i in range(100):
                group.equal(i, i)

    @testcase(summarize=True, num_passing=2, num_failing=3)
    def testcase_level_summarization(self, env, result):
        for i in range(100):
            result.equal(i, i)

    @testcase
    def test_exception_assertions(self, env, result):
        with result.raises(KeyError, description='key error description'):
            {}['foo']

        with result.not_raises(TypeError):
            {}['foo']

        with result.raises(TypeError, pattern='hello'):
            raise TypeError('hello world')

        class MyException(Exception):

            def __init__(self, num, msg):
                super(MyException, self).__init__(msg)
                self.num = num

        with result.raises(MyException, func=lambda exc: exc.num % 2 == 0):
            raise MyException(4, 'exception msg')

    @testcase
    def test_equal_slices_assertions(self, env, result):
        result.equal_slices(
            expected=['a', 'b', 3, 4],
            actual=[1, 2, 3, 4],
            slices=[slice(2, None)],
            description='passing equal slices'
        )

        result.equal_exclude_slices(
            expected=['a', 'b', 3, 4],
            actual=[1, 2, 3, 4],
            slices=[slice(0, 2)],
            description='passing equal exclude slices'
        )

    @testcase
    def test_column_contain(self, env, result):
        table = [
            ['foo', 'bar'],
            [1, 2],
            [10, 20],
            [30, 40],
            [0, 0],
            [100, 200],
            [1000, 2000],
            [10000, 20000]
        ]

        result.table.column_contain(
            table=table,
            column='foo',
            values=[1, 5, 10, 30, 50],
            description='column contain passing',
            limit=3,
        )

    @testcase
    def test_table_match(self, env, result):
        table = [
            ['name', 'value'],
            ['aaa', 1],
            ['bbb', 2],
            ['ccc', 3],
            ['ddd', 4],
        ]

        result.table.match(
            actual=table,
            expected=table,
            description='basic table match')

        result.table.match(
            actual=table,
            expected=table[:-1] + [[always_true, 4]])

        result.table.match(
            actual=table,
            expected=table[:-1] + [[re.compile(r'd+'), 4]])

        table_2 = [
            ['name', 'value', 'is_finished'],
            ['aaa', 10, True],
            ['bbb', 20, False],
            ['ccc', 30, True],
            ['ddd', 40, False],
        ]

        result.table.match(
            actual=table_2,
            expected=table,
            include_columns=['name'],
            report_all=False
        )

        result.table.match(
            actual=table_2,
            expected=table,
            include_columns=['name'],
            report_all=True,
        )

        result.table.match(
            actual=table_2,
            expected=table,
            exclude_columns=['value', 'is_finished'],
            report_all=False,
        )

        result.table.match(
            actual=table_2,
            expected=table,
            exclude_columns=['value', 'is_finished'],
            report_all=True,
        )

    @testcase
    def test_table_log(self, env, result):
        table = [
            ['name', 'value'],
            ['aaa', 1],
            ['bbb', 2],
            ['ccc', 3],
            ['ddd', 4],
        ]

        result.table.log(
            table=table,
            description='basic table log'
        )

        result.table.log(
            table=table,
            display_index=True
        )

    @testcase
    def test_xml_check(self, env, result):

        # Passing assertions
        result.xml.check(
            element='<Root><Test>Foo</Test></Root>',
            xpath='/Root/Test',
            description='basic XML check'
        )

        result.xml.check(
            element='<Root><Test>Value1</Test><Test>Value2</Test></Root>',
            xpath='/Root/Test',
            tags=['Value1', 'Value2'],
        )

        result.xml.check(
            element='<Root><Test>Value1</Test><Test>Value2</Test></Root>',
            xpath='/Root/Test',
            tags=[
                cmp.In(['a', 'b', 'Value1']),
                re.compile('.*lue2')
            ],
        )

        result.xml.check(
            element='''
                <SOAP-ENV:Envelope
                   xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
                    <SOAP-ENV:Header/>
                      <SOAP-ENV:Body>
                        <ns0:message
                         xmlns:ns0="http://testplan">Hello world!</ns0:message>
                      </SOAP-ENV:Body>
                </SOAP-ENV:Envelope>
            ''',
            xpath='//*/a:message',
            tags=['Hello*'],
            namespaces={"a": "http://testplan"},
        )

    @testcase
    def test_dict_check(self, env, result):

        result.dict.check(
            dictionary={'foo': 1, 'bar': 2},
            has_keys=['foo'], absent_keys=['baz'],
            description='basic dict check'
        )

    @testcase
    def test_dict_match(self, env, result):

        result.dict.match(
            actual={'foo': 1, 'bar': 2, 'baz': 2},
            expected={'foo': 1, 'bar': 2, 'bat': 3},
            description='basic dict match',
            actual_description='description for actual',
            expected_description='description for expected',
            include_keys=['foo', 'bar'],
            exclude_keys=['baz', 'bat']
        )

        result.dict.match(
            actual={'foo': 1, 'bar': 'hello'},
            expected={
                'foo': cmp.Equal(1),
                'bar': re.compile('he*')
            },
            description='match with regex & custom func'
        )

    @testcase
    def test_dict_match_all(self, env, result):
        result.dict.match_all(
            values=[
                {'foo': 1, 'bar': 2},
                {'foo': 10, 'bar': 20}
            ],
            comparisons=[
                cmp.Expected({'foo': 10, 'bar': 20}),
                cmp.Expected({'foo': 1, 'bar': 2}),
            ],
            description='basic unordered dict match all'
        )

    @testcase
    def test_fix_check(self, env, result):

        result.fix.check(
            msg={'foo': 1, 'bar': 2},
            has_tags=['foo'], absent_tags=['baz'],
            description='basic fix check'
        )

    @testcase
    def test_fix_match(self, env, result):
        result.fix.match(
            actual={'foo': 1, 'bar': 2, 'baz': 2},
            expected={'foo': 1, 'bar': 2, 'bat': 3},
            description='basic fix match',
            actual_description='description for actual',
            expected_description='description for expected',
            include_tags=['foo', 'bar'],
            exclude_tags=['baz', 'bat']
        )

        result.fix.match(
            actual={'foo': 1, 'bar': 'hello'},
            expected={
                'foo': cmp.Equal(1),
                'bar': re.compile('he*')
            },
            description='match with regex & custom func'
        )

    @testcase
    def test_fix_match_all(self, env, result):
        result.fix.match_all(
            values=[
                {'foo': 1, 'bar': 2},
                {'foo': 10, 'bar': 20}
            ],
            comparisons=[
                cmp.Expected({'foo': 10, 'bar': 20}),
                cmp.Expected({'foo': 1, 'bar': 2}),
            ],
            description='basic unordered fix match all'
        )


def make_multitest():
    return MultiTest(name='MyMultitest', suites=[MySuite()])
