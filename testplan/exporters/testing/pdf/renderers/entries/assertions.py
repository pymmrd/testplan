from cgi import escape

from reportlab.lib import colors
from reportlab.platypus import Paragraph

from testplan.common.exporters.pdf import RowStyle, create_table
from testplan.common.exporters.pdf import format_table_style, format_cell_data
from testplan.common.utils.comparison import is_regex

from testplan.report.testing import Status

from testplan.testing.multitest.entries import assertions

from .base import SerializedEntryRenderer, registry
from .. import constants as const
from ..base import RowData


def _format_text(text, colour, bold=False):
    text = '<font color={colour}>{text}</font>'.format(text=text, colour=colour)
    if bold:
        return '<b>{text}</b>'.format(text=text)
    return text


def default_assertion_style(depth, passed):
    styles = [
        RowStyle(
            font=(
                const.FONT if passed else const.FONT_BOLD,
                const.FONT_SIZE_SMALL
            ),
            left_padding=const.INDENT * depth,
        ),
        RowStyle(
            text_color=colors.green if passed else colors.red,
            start_column=const.LAST_COLUMN_IDX
        )
    ]

    if not passed:
        styles.append(RowStyle(background=colors.whitesmoke))
    return styles


@registry.bind_default(category='assertion')
class AssertionRenderer(SerializedEntryRenderer):
    """Default fallback for rendering serialized assertion entries."""

    def get_header(self, source, depth, row_idx):
        passed = source['passed']

        return RowData(
            content=[
                source['description'] or source['type'],
                '',
                '',
                (Status.PASSED if passed else Status.FAILED).title()
            ],
            style=default_assertion_style(
                passed=passed,
                depth=depth
            ),
            start=row_idx
        )

    def get_detail(self, source, depth, row_idx):
        pass

    def get_row_data(self, source, depth, **kwargs):
        header = self.get_header(source, depth, **kwargs)

        if self.get_style(source).display_assertion_detail:
            detail = self.get_detail(source, depth, row_idx=header.end)
            if detail:
                return header + detail
        return header


@registry.bind(
    assertions.Equal,
    assertions.NotEqual,
    assertions.Greater,
    assertions.GreaterEqual,
    assertions.Less,
    assertions.LessEqual
)
class FunctionAssertionRenderer(AssertionRenderer):
    """
    Basic assertion renderer for serialized assertion entries:
      * Equal
      * NotEqual
      * Greater
      * GreaterEqual
      * Less
      * LessEqual
    """

    def get_detail(self, source, depth, row_idx):
        return RowData(
            content=[
                '{first} {label} {second}'.format(**source),
                '', '', '',
            ],
            style=default_assertion_style(
                passed=source['passed'],
                depth=depth + 1
            ),
            start=row_idx,
        )


@registry.bind(
    assertions.IsClose
)
class ApproximateEqualityAssertionRenderer(AssertionRenderer):
    """
    Assertion renderer for serialized assertion entries:
      * IsClose
    """

    def get_detail(self, source, depth, row_idx):
        return RowData(
            content=[
                '{first} {label} {second}'
                ' (rel_tol: {rel_tol}, abs_tol: {abs_tol})'.format(**source),
                '', '', '',
            ],
            style=default_assertion_style(
                passed=source['passed'],
                depth=depth + 1
            ),
            start=row_idx,
        )


@registry.bind(
    assertions.RegexMatch,
    assertions.RegexSearch,
)
class RegexMatchRenderer(AssertionRenderer):
    """RegexMatch renderer for serialized assertion entries."""
    highlight_color = 'green'
    bold = False

    def get_detail(self, source, depth, row_idx):
        """
            Return highlighted patterns within the
            string, if there is a match.
        """
        pattern_style = [
            RowStyle(
                font=(const.FONT, const.FONT_SIZE_SMALL),
                left_padding=const.INDENT * (depth + 1),
                text_color=colors.black,
                span=tuple()
            ),
        ]

        text_style = [
            RowStyle(
                left_padding=const.INDENT * (depth + 1),
                span=tuple()
            ),
        ]

        if not source['passed']:
            pattern_style.append(RowStyle(background=colors.whitesmoke))
            text_style.append(RowStyle(background=colors.whitesmoke))

        p = 'Pattern: `{}`'.format(source['pattern'])
        pattern = RowData(
            content=[p, '', '', ''],
            style=pattern_style,
            start=row_idx
        )

        string = source['string']
        if source['match_indexes']:
            curr_idx = 0
            parts = []

            for begin, end in source['match_indexes']:
                if begin > curr_idx:
                    s = string[curr_idx:begin].replace('\n', '<br />\n')
                    parts.append(s)
                s = string[begin:end].replace('\n','<br />\n')
                parts.append(_format_text(s, self.highlight_color, self.bold))
                curr_idx = end

            if curr_idx < len(string):
                s = string[curr_idx:].replace('\n','<br />\n')
                parts.append(s)
            text_paragraph = Paragraph(
                text=''.join(parts),
                style=const.PARAGRAPH_STYLE
            )
        else:
            text_paragraph = Paragraph(
                text=string,
                style=const.PARAGRAPH_STYLE
            )

        return pattern + RowData(content=[text_paragraph, '', '', ''],
                                 style=text_style,
                                 start=pattern.end)


@registry.bind(
    assertions.RegexMatchNotExists,
    assertions.RegexSearchNotExists
)
class RegexNotMatchRenderer(RegexMatchRenderer):
    """RegexNotMatch renderer for serialized assertion entries."""
    highlight_color = 'red'
    bold = True


@registry.bind(assertions.RegexFindIter)
class RegexFindIterRenderer(RegexMatchRenderer):
    """RegexFindIter renderer for serialized assertion entries."""

    def get_detail(self, source, depth, row_idx):
        """Render `condition` attribute as well, if it exists"""
        styles = [
            RowStyle(
                font=(const.FONT, const.FONT_SIZE_SMALL),
                left_padding=const.INDENT * (depth + 1),
                top_padding=0,
                text_color=colors.black,
                span=tuple()
            ),
        ]

        if not source['passed']:
            styles.append(RowStyle(background=colors.whitesmoke))

        msg = super(RegexFindIterRenderer, self).get_detail(
            source,
            depth,
            row_idx
        )
        if source['condition_match'] is not None:
            colour = 'green' if source['condition_match'] else 'red'
            formatted = 'Condition: {}'.format(_format_text(
                text=escape(source['condition']),
                colour=colour,
                bold=not source['condition_match']
            ))
            condition = Paragraph(
                text=formatted,
                style=const.PARAGRAPH_STYLE
            )
            msg += RowData(
                content=[condition, '', '', ''],
                style=styles,
                start=msg.end
            )
        return msg


@registry.bind(assertions.RegexMatchLine)
class RegexMatchLineRenderer(AssertionRenderer):
    """RegexMatchLine renderer for serialized assertion entries."""

    def get_detail(self, source, depth, row_idx):
        """
        `RegexMatchLine` returns line indexes
        along with begin/end character indexes per matched line.
        """
        pattern_style = [
            RowStyle(
                font=(const.FONT, const.FONT_SIZE_SMALL),
                left_padding=const.INDENT * (depth + 1),
                text_color=colors.black,
                span=tuple()
            ),
        ]

        text_style = [
            RowStyle(
                left_padding=const.INDENT * (depth + 1),
                span=tuple()
            ),
        ]

        if not source['passed']:
            pattern_style.append(RowStyle(background=colors.whitesmoke))
            text_style.append(RowStyle(background=colors.whitesmoke))

        p = 'Pattern: `{}`'.format(source['pattern'])
        pattern = RowData(
            content=[p, '', '', ''],
            style=pattern_style,
            start=row_idx
        )

        if source['match_indexes']:
            parts = []
            match_map = {
                line_no: (begin, end)
                for line_no, begin, end in source['match_indexes']
                }

            for idx, line in enumerate(source['string'].splitlines()):
                if idx in match_map:
                    begin, end = match_map[idx]
                    formatted = '{start}{middle}{end}'.format(
                        start=escape(line[:begin]),
                        middle=_format_text(
                            text=escape(line[begin:end]),
                            colour='green',
                            bold=False
                        ),
                        end=escape(line[end:]))
                    parts.append(formatted)
                else:
                    parts.append(escape(line))
            text = Paragraph(
                text='<br />\n'.join(parts),
                style= const.PARAGRAPH_STYLE
            )
        else:
            formatted = escape(source['string']).replace('\n', '<br />\n')
            text = Paragraph(
                text=formatted,
                style=const.PARAGRAPH_STYLE
            )

        return pattern + RowData(content=[text, '', '', ''],
                                 style=text_style,
                                 start=pattern.end)


@registry.bind(
    assertions.Contain,
    assertions.NotContain
)
class MembershipRenderer(AssertionRenderer):
    """Contain & NotContain renderer for serialized assertion entries."""

    def get_detail(self, source, depth, row_idx):
        """Return the member and container representations"""
        passed = source['passed']

        styles = [
            RowStyle(
                font=(
                    const.FONT if passed else const.FONT_BOLD,
                    const.FONT_SIZE_SMALL
                ),
                left_padding=const.INDENT * (depth + 1),
                text_color=colors.black if passed else colors.red
            )
        ]

        if not passed:
            styles.append(RowStyle(background=colors.whitesmoke))

        op_label = 'in' if source['type'] == 'Contain' else 'not in'
        text = '{} {} {}'.format(
            source['member'],
            op_label,
            source['container']
        )

        return RowData(
            content=[text, '', '', ''],
            style=styles,
            start=row_idx
        )


def append_comparison_data(data, row, depth, start_idx):
    """TODO."""
    offset, key, match, left, right = row

    if match == 'Passed':
        item_color = colors.black
        status_color = colors.green
        font = const.FONT
    elif match == 'Failed':
        item_color = colors.black
        status_color = colors.red
        font = const.FONT_BOLD
    else:
        item_color = colors.grey
        status_color = colors.grey
        font = const.FONT_ITALIC

    if isinstance(left, tuple):
        left = '<{}> {}'.format(left[0], left[1])
    if isinstance(right, tuple):
        right = '<{}> {}'.format(right[0], right[1])

    data.append(
        RowData(
            content=[key, left, right, match],
            style=[
                RowStyle(
                    text_color=item_color,
                    font=(font, const.FONT_SIZE_SMALL),
                    left_padding=const.INDENT * (depth + offset + 1),
                ),
                RowStyle(
                    text_color=status_color,
                    start_column=const.LAST_COLUMN_IDX
                )
            ],
            start=start_idx,
        )
    )


@registry.bind(
    assertions.FixMatch,
    assertions.DictMatch
)
class FixMatchRenderer(AssertionRenderer):
    """FixMatch renderer for serialized assertion entries."""

    def get_detail(self, source, depth, row_idx):
        comparison = source['comparison']

        data = []

        for idx, row in enumerate(comparison):
            append_comparison_data(data, row, depth, row_idx + idx)

        first, rest = data[0], data[1:]

        for d in rest:
            first += d

        return first


@registry.bind(
    assertions.FixCheck,
    assertions.DictCheck
)
class FixCheckRenderer(AssertionRenderer):
    """FixCheck renderer for serialized assertion entries."""

    def get_detail(self, source, depth, row_idx):
        """Return `has_keys` & `absent_keys` context"""
        result = None
        end_idx = row_idx
        check = {'has_keys': 'Existence check', 'absent_keys': 'Absence check'}
        diff = {
            'has_keys': 'Missing keys',
            'absent_keys': 'Key should be absent'
        }

        for keys in ['has_keys', 'absent_keys']:

            if source[keys]:
                check_style = RowStyle(
                    font=(const.FONT, const.FONT_SIZE_SMALL),
                    left_padding=const.INDENT * (depth + 1),
                    text_color=colors.black,
                    span=tuple()
                )
                text = '{}: {}'.format(check[keys], source[keys])
                check_row = RowData(
                    content=text,
                    style=check_style,
                    start=end_idx
                )
                if result is None:
                    result = check_row
                else:
                    result += check_row

                if source['{}_diff'.format(keys)]:
                    text = '{}: {}'.format(
                        diff[keys],
                        _format_text(
                            text=source['{}_diff'.format(keys)],
                            colour='red',
                            bold=True
                        )
                    )
                    diff_para = Paragraph(
                        text=text,
                        style=const.PARAGRAPH_STYLE
                    )
                    pad = const.INDENT * (depth + 2)
                    diff_style = RowStyle(
                        left_padding=pad,
                        bottom_padding=0,
                        span=tuple()
                    )
                    diff_row = RowData(
                        content=[diff_para, '', '', ''],
                        style=diff_style,
                        start=check_row.end
                    )
                    end_idx = diff_row.end
                    result += diff_row

        return result


@registry.bind(
    assertions.FixMatchAll,
    assertions.DictMatchAll
)
class FixMatchAllRenderer(AssertionRenderer):
    """FixMatchAll renderer for serialized assertion entries."""

    def get_detail(self, source, depth, row_idx):
        matches = source['matches']

        data = []
        counter = 0
        for match in matches['matches']:
            comparison = match['comparison']
            description = match['description']
            passed = match['passed']

            # Description row styles
            styles = [
                RowStyle(
                    font=(
                        const.FONT if passed else const.FONT_BOLD,
                        const.FONT_SIZE_SMALL
                    ),
                    left_padding=const.INDENT * (depth + 1),
                ),
                RowStyle(
                    text_color=colors.green if passed else colors.red,
                    start_column=const.LAST_COLUMN_IDX
                )
            ]

            # Description row data
            data.append(RowData(
                content=[
                    description, '', '',
                    (Status.PASSED if passed else Status.FAILED).title()
                ],
                style=styles,
                start=row_idx + counter
            ))
            counter += 1

            for row in comparison:
                append_comparison_data(data, row, depth, row_idx + counter)
                counter += 1

            # Empty row after each matched entry
            data.append(
                RowData(
                    content=['', '', '', ''],
                    start=row_idx + counter
                )
            )
            counter += 1

        first, rest = data[0], data[1:]

        for d in rest:
            first += d

        return first


@registry.bind(assertions.XMLCheck)
class XMLCheckRenderer(AssertionRenderer):
    """XMLCheck renderer for serialized assertion entries."""

    def get_detail(self, source, depth, row_idx):
        """
        Render the message if there is any, then render XMLTagComparison items.
        """
        msg = []

        msg.append('xpath: {}'.format(escape(source['xpath'])))

        if source['namespaces']:
            msg.append(
                'Namespaces: {}'.format(
                    escape(
                        str(
                            source['namespaces']
                        )
                    )
                )
            )

        if source['message']:
            msg.append(
                _format_text(
                    colour='black' if source['passed'] else 'red',
                    text=escape(source['message']),
                    bold = not source['passed']
                )
            )

        if source['data']:
            msg.append('Tags:')

        msg_style = RowStyle(
            left_padding=const.INDENT * (depth + 1),
            bottom_padding=0,
            span=tuple()
        )
        msg_para = Paragraph(
            text='<br />\n'.join(msg),
            style=const.PARAGRAPH_STYLE
        )
        msg_row = RowData(
            content=[msg_para, '', '', ''],
            style=msg_style,
            start=row_idx
        )

        tags = []
        for data in source['data']:
            tag_comp = assertions.XMLTagComparison(
                tag=data[0],
                diff=data[1],
                error=data[2],
                extra=data[3]
            )
            template = '{actual} {operator} {expected}'
            common = dict(
                actual=tag_comp.tag,
                expected=tag_comp.comparison_value
            )

            if tag_comp.passed:
                tags.append(
                    escape(
                        template.format(
                            operator='==', **common
                        )
                    )
                )
            else:
                tags.append(
                    _format_text(
                        text=escape(
                            template.format(
                                operator='!=', **common
                            )
                        ),
                        colour='red',
                        bold=True
                    )
                )

        if tags:
            tags_style = RowStyle(
                left_padding=const.INDENT * (depth + 2),
                span=tuple()
            )
            tags_para = Paragraph(
                text='<br />\n'.join(tags),
                style=const.PARAGRAPH_STYLE
            )
            tags_row = RowData(
                content=[tags_para, '', '', ''],
                style=tags_style,
                start=msg_row.end
            )

            return msg_row + tags_row
        else:
            return msg_row


@registry.bind(assertions.TableMatch)
class TableMatchRenderer(AssertionRenderer):
    """
    Renders serialized tabular data in ReportLab table format.
    """

    def get_matched_row_data(self, row_comparison, columns, include_columns,
                             exclude_columns, row_idx):
        """
        Return a single row of data in the correct match format and the
        RowStyles indicating which cells need to be coloured red.

        Sample output:

        [{'name': Susan == Susan, 'age': 24 == 24}]

        and

        [RowStyle(...), ...]


        :param row_comparison: RowComparison object containing this rows data.
        :type row_comparison: ``testplan.testing.multitest
                                .entries.assertions.RowComparison``
        :param columns: List of the displayed columns.
        :type columns: ``list``
        :param row_idx: Index of the row being compared. This is not the same as
                        other row_idx parameters in this module. Those refer to
                        the row index of the global table used to display
                        everything in the PDF report.
        :type row_idx: ``int``
        :param include_columns:
        :type include_columns:
        :param exclude_columns:
        :type exclude_columns:
        :return: A single row of the matched data in tabular format and the
                 RowStyles indicating which cells need to be coloured red.
        :rtype: ``list`` of ``dict`` and
                ``list`` of ``testplan.common.exporters.pdf.RowStyle``
        """
        result = {}
        colour_row = []

        for idx, column in enumerate(columns):
            actual = row_comparison.data[idx]
            other, matched = row_comparison.get_comparison_value(column, idx)

            value_limit = int((const.CELL_STRING_LENGTH - 4) / 2)
            other, actual = format_cell_data(
                data=[other, actual],
                limit=value_limit
            )

            other = "REGEX('{}')".format(
                other.pattern) if is_regex(other) else other

            include_columns = include_columns or columns
            exclude_columns = exclude_columns or []

            if (column not in include_columns) or (column in exclude_columns):
                result[column] = '{} .. {}'.format(actual, other)
                colour_row.append('I')
            elif matched:
                result[column] = '{} == {}'.format(actual, other)
                colour_row.append('P')
            else:
                result[column] = '{} != {}'.format(actual, other)
                colour_row.append('F')

        return result, colour_row

    def get_detail(self, source, depth, row_idx):
        row_style = [RowStyle(left_padding=const.INDENT * (depth + 1))]
        table_style = format_table_style(const.DISPLAYED_TABLE_STYLE)

        raw_table = []
        row_indices = []
        colour_matrix = []
        for i, row_comparison_data in enumerate(source['data']):
            row_comparison = assertions.RowComparison(*row_comparison_data)
            row, colour_row = self.get_matched_row_data(
                row_comparison=row_comparison,
                columns=source['columns'],
                include_columns=source['include_columns'],
                exclude_columns=source['exclude_columns'],
                row_idx=i
            )
            raw_table.append(row)
            row_indices.append(row_comparison.idx)
            colour_matrix.append(colour_row)

        max_width = const.PAGE_WIDTH - (depth * const.INDENT)
        display_index = source['fail_limit'] > 0
        table = create_table(
            table=raw_table,
            columns=source['columns'],
            row_indices=row_indices,
            display_index=display_index,
            max_width=max_width,
            style=table_style,
            colour_matrix=colour_matrix
        )

        if source['message']:
            error_style = row_style + [RowStyle(textcolor=colors.red)]
            error = RowData(
                content=source['message'],
                start=row_idx,
                style=error_style
            )
            # The error style isn't applied to the error string, possible bug.
            return error + RowData(
                content=table,
                start=error.end,
                style=row_style
            )
        else:
            return RowData(content=table, start=row_idx, style=row_style)


@registry.bind(assertions.ColumnContain)
class ColumnContainRenderer(AssertionRenderer):
    """ColumnContain renderer for serialized assertion entries."""

    def get_detail(self, source, depth, row_idx):
        row_style = RowStyle(
            left_padding=const.INDENT * (depth + 1),
            font=(const.FONT, const.FONT_SIZE_SMALL)
        )
        table_style = format_table_style(const.DISPLAYED_TABLE_STYLE)

        raw_table = []
        row_indices = []
        colour_matrix = []
        for comp_obj in source['data']:
            row = {
                source['column']: comp_obj[1],
                'Passed': 'Pass' if comp_obj[2] else 'Fail'
            }
            raw_table.append(row)
            row_indices.append(comp_obj[0])
            colour_matrix.append(['I', 'P' if comp_obj[2] else 'F'])

        max_width = const.PAGE_WIDTH - (depth * const.INDENT)
        table = create_table(
            table=raw_table,
            columns=[source['column'], 'Passed'],
            row_indices=row_indices,
            display_index=source['report_fails_only'],
            max_width=max_width,
            style=table_style,
            colour_matrix=colour_matrix
        )

        data = [['Values: {}'.format(source['values']), '', '', '']] + table
        return RowData(content=data, start=row_idx, style=row_style)


@registry.bind(
    assertions.ExceptionRaised,
    assertions.ExceptionNotRaised
)
class ExceptionRaisedRenderer(AssertionRenderer):
    """ExceptionRaised renderer for serialized assertion entries."""

    def get_detail(self, source, depth, row_idx):

        raised_exc = source['raised_exception']
        expected_exceptions = ', '.join(source['expected_exceptions'])

        label = 'not instance of' if source['type'] == 'ExceptionNotRaised' \
            else 'instance of'

        msg = '{} {} {}'.format(raised_exc[0], label, expected_exceptions)
        exc_style = RowStyle(
            left_padding=const.INDENT * (depth + 1),
            font=(const.FONT, const.FONT_SIZE_SMALL),
            text_color=colors.black
        )
        exc_row = RowData(content=msg, style=exc_style, start=row_idx)
        end_idx = exc_row.end

        if source['func']:
            msg = 'Function: {}'.format(
                _format_text(
                    colour='black' if source['passed'] else 'red',
                    text=escape(source['func']),
                    bold=not source['passed']
                )
            )
            func_paragraph = Paragraph(
                text=msg,
                style=const.PARAGRAPH_STYLE
            )
            func_style = RowStyle(
                left_padding=const.INDENT * (depth + 2),
                span=()
            )
            func_row = RowData(
                content=[func_paragraph, '', '', ''],
                style=func_style,
                start=end_idx
            )
            exc_row += func_row
            end_idx = func_row.end

        if source['pattern']:
            msg = 'Pattern: {}'.format(
                _format_text(
                    colour='black' if source['passed'] else 'red',
                    text=escape(source['pattern']),
                    bold=not source['passed']
                )
            )
            msg += '<br />Exception message: {}'.format(raised_exc[1])
            ptrn_paragraph = Paragraph(
                text=msg,
                style=const.PARAGRAPH_STYLE
            )
            ptrn_style = RowStyle(
                left_padding=const.INDENT * (depth + 2),
                span=()
            )
            exc_row += RowData(
                content=[ptrn_paragraph, '', '', ''],
                style=ptrn_style,
                start=end_idx
            )

        return exc_row


@registry.bind(assertions.EqualSlices)
class EqualSlicesRenderer(AssertionRenderer):
    """EqualSlices renderer for serialized assertion entries."""

    def get_detail(self, source, depth, row_idx):
        result = None
        for slice, _, mismatch_indices, actual, expected in source['data']:
            passed = not mismatch_indices
            slice_style = RowStyle(
                font=(
                    const.FONT if passed else const.FONT_BOLD,
                    const.FONT_SIZE_SMALL
                ),
                left_padding=const.INDENT * (depth + 1),
                text_color=colors.black if passed else colors.red
            )
            slice_row = RowData(content=slice, style=slice_style, start=row_idx)
            if result is None:
                result = slice_row
            else:
                result += slice_row

            # Display mismatched indexes if slice has
            # a step, for easier debugging
            indices_style = RowStyle(
                font=(const.FONT, const.FONT_SIZE_SMALL),
                left_padding=const.INDENT * (depth + 2),
                text_color = colors.black,
                span=tuple()
            )
            indices = []
            if not passed:
                indices.append(
                    'Mismatched indices: {}'.format(
                        mismatch_indices
                    )
                )
            indices.append('Actual:        {}'.format(actual))
            indices.append('Expected:   {}'.format(expected))
            indices_para = Paragraph(
                text='<br />\n'.join(indices),
                style=const.PARAGRAPH_STYLE
            )
            indices_row = RowData(
                content=[indices_para, '', '', ''],
                style=indices_style,
                start=slice_row.end
            )
            result += indices_row
            row_idx = indices_row.end

        return result

@registry.bind(assertions.EqualExcludeSlices)
class EqualExcludeSlicesRenderer(AssertionRenderer):
    """EqualExcludeSlices renderer for serialized assertion entries."""
    def get_detail(self, source, depth, row_idx):
        result = None
        end_idx = row_idx
        for slice, _, mismatch_indices, actual, expected in source['data']:
            slice_style = RowStyle(
                font=(const.FONT, const.FONT_SIZE_SMALL),
                left_padding=const.INDENT * (depth + 1),
                text_color=colors.black
            )
            slice_row = RowData(
                content='{} - excluded'.format(slice),
                style=slice_style,
                start=end_idx
            )
            if result is None:
                result = slice_row
            else:
                result += slice_row
            end_idx = slice_row.end
        actual = [source['actual'][i] for i in source['included_indices']]
        expected = [source['expected'][i] for i in source['included_indices']]
        passed = source['passed']

        indices = [
            '{}: {}'.format(
                title,
                _format_text(
                    text=data,
                    colour='black' if passed else 'red',
                    bold=not passed
                )
            )
            for title, data in (
                ('Compared indices', source['included_indices']),
                ('Actual', actual),
                ('Expected', expected)
            )
        ]

        indices_para = Paragraph(
            text='<br />\n'.join(indices),
            style=const.PARAGRAPH_STYLE
        )
        indices_style = RowStyle(
            left_padding=const.INDENT * (depth + 1),
            span=tuple()
        )
        indices_row = RowData(
            content=[indices_para, '', '', ''],
            style=indices_style,
            start=end_idx
        )
        return result + indices_row


@registry.bind(assertions.RawAssertion)
class RawAssertionRenderer(AssertionRenderer):

    def get_detail(self, source, depth, row_idx):
        return RowData(
            content=source['content'],
            start=row_idx,
            style=default_assertion_style(
                depth=depth + 1,
                passed=source['passed']
            )
        )
