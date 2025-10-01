#!/usr/bin/env python3
"""
PENSA MENSA NEWSLETTER GENERATOR - COMPLETE VERSION
Usage: python final_generator.py [json_file] [output_file]
Default: python final_generator.py ./pensa_mensa_content.json ./newsletter.pdf
"""

import json
import calendar
import sys
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch  # inch = 72.0 points
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.pdfgen import canvas
import re

class PageNumCanvas(canvas.Canvas):
    """Canvas with centered page numbers"""
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []
        
    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()
        
    def save(self):
        for page in self.pages:
            self.__dict__.update(page)
            self.draw_page_number()
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
        
    def draw_page_number(self):
        self.setFont("Helvetica", 9)
        self.drawCentredString(letter[0] / 2, 1*inch, str(self._pageNumber))

class ContinuableBox(Flowable):
    """A box that can split across pages with continuation header"""
    def __init__(self, title, content_elements, width=6.5*inch):
        Flowable.__init__(self)
        self.title = title
        self.content_elements = content_elements if content_elements else []
        self.width = width
        self.height = 0
        # Note: hAlign doesn't work reliably for custom Flowables
        # ReportLab centers flowables by default in the available width

    def wrap(self, availWidth, availHeight):
        """Calculate size needed"""
        header_height = 0.3*inch
        content_height = 0

        for elem in self.content_elements:
            if hasattr(elem, 'wrap'):
                w, h = elem.wrap(self.width - 10, 10000)  # Get actual full height
                content_height += h + 3  # Small padding between elements

        total_height = header_height + content_height + 6  # Top and bottom padding

        # Set height for drawing - use what's available or what we need, whichever is less
        self.height = min(total_height, availHeight)

        # But return actual height needed so ReportLab knows if splitting is required
        return (self.width, total_height)

    def split(self, availWidth, availHeight):
        """Split across pages if needed"""
        if not self.content_elements:
            return None

        header_height = 0.3*inch
        padding = 6  # Top and bottom content padding
        min_box_height = header_height + 1*inch  # Minimum sensible box size

        # If available space is too small, don't split - let ReportLab move whole thing to next page
        if availHeight < min_box_height:
            return []  # Return empty list = can't split, try on next page

        # Calculate total height needed for all content
        total_content_height = 0
        for elem in self.content_elements:
            if hasattr(elem, 'wrap'):
                w, h = elem.wrap(self.width - 10, 10000)
                total_content_height += h + 3

        total_height = header_height + total_content_height + padding

        # If everything fits, no split needed
        if total_height <= availHeight:
            return None

        # Find how many elements fit in available space
        available_for_content = availHeight - header_height - padding
        current_height = 0
        split_index = 0

        for i, elem in enumerate(self.content_elements):
            if hasattr(elem, 'wrap'):
                w, h = elem.wrap(self.width - 10, 10000)
                if current_height + h + 3 > available_for_content:
                    # This element doesn't fit
                    break
                current_height += h + 3
                split_index = i + 1

        # If we can't fit even one element, move entire box to next page
        if split_index == 0:
            return []

        # If all elements fit, no split needed
        if split_index >= len(self.content_elements):
            return None

        # Create continuation boxes
        first_box = ContinuableBox(self.title, self.content_elements[:split_index], self.width)
        second_box = ContinuableBox(f"{self.title}, continued", self.content_elements[split_index:], self.width)

        return [first_box, second_box]

    def draw(self):
        """Draw the box"""
        c = self.canv

        # Shift left by 43/512 inch to align with Tables (which have different positioning)
        x_offset = -0.083984375*inch

        # Draw header
        c.setFillColor(colors.lightgrey)
        c.rect(x_offset, self.height - 0.3*inch, self.width, 0.3*inch, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(self.width/2 + x_offset, self.height - 0.2*inch, self.title)

        # Draw content area border
        c.rect(x_offset, 0, self.width, self.height - 0.3*inch, fill=0, stroke=1)

        # Draw content elements
        y_pos = self.height - 0.3*inch - 3  # Start below header with top padding
        for elem in self.content_elements:
            if hasattr(elem, 'wrap'):
                w, h = elem.wrap(self.width - 10, 10000)
                # Only draw if there's space
                if y_pos - h >= 0:
                    elem.drawOn(c, 5 + x_offset, y_pos - h)
                    y_pos -= h + 3

class NewsletterHeader(Flowable):
    """Header with 300% scaled logo and dynamic text"""
    def __init__(self, config):
        self.config = config
        self.width = 6.5*inch
        self.height = 1.4*inch
        
    def draw(self):
        c = self.canv
        
        # Main logo - scaled to 300%
        if os.path.exists('./1759076190797_image.jpg'):
            try:
                logo_width = 3.9*inch  # ~300% of 1.3*inch
                logo_height = logo_width * 0.27  # 27% aspect ratio
                
                c.drawImage('./1759076190797_image.jpg', 
                           -0.15*inch, 0.8*inch,
                           width=logo_width, height=logo_height,
                           preserveAspectRatio=True, mask='auto')
            except:
                pass
        
        # Static text image (adjusted for 6.5" width)
        if os.path.exists('./logo_text_right-top.jpg'):
            try:
                c.drawImage('./logo_text_right-top.jpg',
                           3.9*inch, 1.3*inch,  # Shifted left by 0.5"
                           width=3.75*inch, height=0.5*inch,
                           preserveAspectRatio=True, mask='auto')
            except:
                pass

        # Dynamic text (uses self.width so it adjusts automatically)
        c.setFont("Helvetica-Bold", 13)
        c.drawRightString(self.width - 0.125*inch, 1.15*inch, self.config['month_year'])

        c.setFont("Helvetica", 10)
        c.drawRightString(self.width - 0.125*inch, 0.95*inch,
                         f"Volume {self.config['volume']}, Issue {self.config['issue']}")

class NewsletterGenerator:
    def __init__(self, data):
        self.data = data
        self.config = data['config']
        self.static = data.get('static_content', {})
        self.styles = getSampleStyleSheet()
        self.setup_styles()
        
    def setup_styles(self):
        """Create styles with +2px line spacing"""
        self.body_text = ParagraphStyle(
            name='PMBody',
            fontSize=9,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
            leading=13  # +2px from base 11
        )
        
        self.body_text_left = ParagraphStyle(
            name='PMBodyLeft',
            fontSize=9,
            alignment=TA_LEFT,
            spaceAfter=6,
            leading=13
        )
        
        self.body_text_large = ParagraphStyle(
            name='PMBodyLarge',
            fontSize=11,
            alignment=TA_LEFT,
            spaceAfter=6,
            leading=15
        )
        
        self.body_text_bold = ParagraphStyle(
            name='PMBodyBold',
            fontSize=11,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold',
            spaceAfter=6,
            leading=15
        )
        
        self.small_body = ParagraphStyle(
            name='SmallBody',
            fontSize=7,
            alignment=TA_JUSTIFY,
            spaceAfter=4,
            leading=10
        )
        
        self.tiny_text = ParagraphStyle(
            name='TinyText',
            fontSize=7,
            alignment=TA_JUSTIFY,
            spaceAfter=2,
            leading=9
        )
        
        self.article_text = ParagraphStyle(
            name='ArticleText',
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            leading=14
        )
        
        self.cal_event_style = ParagraphStyle(
            name='CalEvent',
            fontSize=6,
            spaceAfter=0,
            leading=6
        )
        
        self.minutes_header = ParagraphStyle(
            name='MinutesHeader',
            fontSize=9,
            alignment=TA_CENTER,
            leading=11
        )
        
        self.minutes_body = ParagraphStyle(
            name='MinutesBody',
            fontSize=8,
            alignment=TA_LEFT,
            leading=10
        )
        
        self.centered_bold = ParagraphStyle(
            name='CenteredBold',
            fontSize=11,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            leading=15
        )
        
        self.centered_normal = ParagraphStyle(
            name='CenteredNormal',
            fontSize=9,
            alignment=TA_CENTER,
            leading=13
        )

        self.officers_style = ParagraphStyle(
            name='OfficersStyle',
            fontSize=10,
            alignment=TA_LEFT,
            leading=15  # fontSize 10 + 2px standard + 3px additional = 15
        )

    def clean_text(self, text):
        """Fix HTML entities and encoding issues"""
        if not text:
            return text
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        text = text.replace('**', '')  # Remove markdown bold
        return text

    def has_html_tags(self, text):
        """Check if text contains any HTML tags"""
        if not text:
            return False
        return bool(re.search(r'<[^>]+>', text))
    
    def strip_all_html(self, text):
        """Remove ALL HTML tags completely while preserving intentional spacing"""
        if not text:
            return text

        # Remove all HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Clean up HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&amp;', '&')

        # Only clean up spaces on individual lines, preserve line breaks
        lines = text.split('\n')
        lines = [re.sub(r'[ \t]+', ' ', line.strip()) for line in lines]
        text = '\n'.join(lines)

        return text.strip()

    def make_urls_blue(self, text):
        """Convert URLs and emails to blue hyperlinks - only converts plain text URLs"""
        if not text:
            return text

        # Skip if text already has link/font tags (already formatted)
        if '<link' in text or '<font color=' in text:
            return text

        # URLs with protocol
        def format_url_with_protocol(match):
            url = match.group(1)
            terminator = match.group(2)
            formatted = f'<font color="#0000FF"><u><link href="{url}">{url}</link></u></font>{terminator}'
            return formatted

        text = re.sub(
            r'\b(https?://[^\s<>]+)([.,;:!?\s]|$)',
            format_url_with_protocol,
            text
        )

        # Email addresses
        text = re.sub(
            r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
            r'<font color="#0000FF"><u><link href="mailto:\1">\1</link></u></font>',
            text
        )

        # www URLs without protocol (but not already part of http://www or https://www)
        text = re.sub(
            r'(?<!://)\b(www\.[^\s<>]+)([.,;:!?\s]|$)',
            r'<font color="#0000FF"><u>\1</u></font>\2',
            text
        )

        return text

    def create_minutes_box(self, title, content, width=6.5*inch):
        """Create ExComm minutes box that splits with continuation header"""
        if isinstance(content, list):
            content_elements = content
        else:
            content_elements = [Paragraph(content, self.body_text_left)]

        # Return the custom splittable box directly (no wrapper to preserve splitting)
        return ContinuableBox(title, content_elements, width)

    def create_box(self, title, content, width=6.5*inch, style=None):
        """Create a bordered box"""
        elements = []
        
        if title:
            title_table = Table([[title]], colWidths=[width])
            title_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(title_table)
        
        if not style:
            style = self.body_text_left
            
        if isinstance(content, list):
            content_elements = content
        else:
            content = self.clean_text(content)
            content = self.make_urls_blue(content)
            para = Paragraph(content, style)
            content_elements = [para]
        
        for elem in content_elements:
            if isinstance(elem, (Paragraph, Spacer, Table, Image)):
                content_table = Table([[elem]], colWidths=[width])
                content_table.setStyle(TableStyle([
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))
                elements.append(content_table)
        
        main_table = Table([[elements]], colWidths=[width])
        main_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        return main_table

    def create_page1(self):
        """Page 1 using content from JSON"""
        story = []
        width = 6.5*inch
        
        # Header
        story.append(NewsletterHeader(self.config))
        story.append(Spacer(1, -0.7*inch))
        
        page1 = self.static.get('page1', {})
        
        # Box 1: Purpose Statement
        box1 = page1.get('box1', {})
        if box1:
            purpose1 = Paragraph(f"<para align='center'><b>{box1.get('line1', '')}</b></para>", 
                                self.centered_bold)
            purpose2_text = self.make_urls_blue(f"<b>{box1.get('line2', '')}</b>")
            purpose2 = Paragraph(purpose2_text, self.body_text_bold)
            story.append(self.create_box(None, [purpose1, purpose2], width))
        
        # Box 2: Organization Info
        box2 = page1.get('box2', {})
        if box2:
            org1 = Paragraph(f"<para align='center'>{box2.get('line1', '')}</para>",
                            self.centered_normal)
            org2 = Paragraph(self.make_urls_blue(self.clean_text(box2.get('content', ''))), self.body_text)
            story.append(self.create_box(None, [org1, org2], width))
        
        # Box 3: Web/Facebook
        box3 = page1.get('box3', {})
        if box3:
            box3_text = self.clean_text(box3.get('content', '')).replace('\n\n', '<br/><br/>')
            story.append(self.create_box(None, self.make_urls_blue(box3_text), width, self.body_text))
        
        # Box 4: American Mensa login
        box4 = page1.get('box4', {})
        if box4:
            box4_text = self.clean_text(box4.get('content', '')).replace('\n\n', '<br/><br/>')
            story.append(self.create_box(None, self.make_urls_blue(box4_text), width, self.small_body))
        
        # Box 5: Mensa International
        box5 = page1.get('box5', {})
        if box5:
            story.append(self.create_box(None, self.make_urls_blue(box5.get('content', '')), width, self.body_text))
        
        # Box 6: Copyright
        box6 = page1.get('box6', {})
        if box6:
            story.append(self.create_box(None, self.clean_text(box6.get('content', '')), width, self.small_body))
        
        return story

    def create_treasurer_report(self):
        """Create Treasurer's Report from JSON"""
        tr = self.static.get('treasurer_report', {})
        if not tr:
            return []

        # Header paragraph with minimal spacing after
        header_style = ParagraphStyle('TreasurerHeader',
                                     parent=self.body_text_large,
                                     spaceAfter=2,  # Minimal space after header
                                     spaceBefore=0)
        header_para = Paragraph(f"<u>{tr.get('date_range', '')}</u>", header_style)

        # Format amounts: add leading and trailing space to positive numbers for alignment
        def format_amount(amount):
            if not amount:
                return amount
            if amount.startswith('('):
                # Negative number - make red (parentheses take up the space)
                return f'<font face="Courier" color="red">({amount[1:]}</font>'
            else:
                # Positive number - add leading space and trailing non-breaking space to match parentheses width
                return f'<font face="Courier" color="blue">&nbsp;{amount}&nbsp;</font>'

        # Create compact paragraph style for amounts with 3px spacing between lines
        compact_style = ParagraphStyle('CompactAmount',
                                       fontSize=11,
                                       fontName='Helvetica',
                                       alignment=TA_RIGHT,
                                       leading=14,  # 11pt + 3px
                                       spaceAfter=3,  # 3px after each line
                                       spaceBefore=0)

        # Create table with Paragraphs (needed to render HTML) but compact styling
        data = [
            ['Beginning balance', Paragraph(format_amount(tr.get('beginning_balance', '')), compact_style)],
            ['Deposits', Paragraph(format_amount(tr.get('deposits', '')), compact_style)],
            ['Checks & deductions', Paragraph(format_amount(tr.get('checks_deductions', '')), compact_style)],
            ['Ending balance', Paragraph(format_amount(tr.get('ending_balance', '')), compact_style)]
        ]

        amounts_table = Table(data, colWidths=[2*inch, 1.25*inch])
        amounts_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        return self.create_box(tr.get('header', 'Treasurer\'s Report'),
                              [header_para, amounts_table],  # Spacing controlled by header_style
                              6.5*inch)

    def create_membership_stats(self):
        """Create Membership Statistics from JSON"""
        ms = self.static.get('membership_stats', {})
        if not ms:
            return []
            
        html = f"""<i>Local group membership changes from {ms.get('date_range', '')}:</i><br/><br/>
{ms.get('entered', 0)} members entered our local group.<br/>
{ms.get('exited', 0)} members exited our local group.<br/><br/>
{ms.get('total', 0)} local group members in total."""
        return self.create_box(ms.get('header', 'Membership Statistics'), html, 6.5*inch, self.body_text_large)

    def create_newsletter_updates(self):
        """Create Newsletter Updates from JSON"""
        nu = self.static.get('newsletter_updates', {})
        if not nu:
            return []
            
        text = f"{nu.get('content', '')}<br/><br/>{nu.get('signature', '').replace(chr(10), '<br/>')}"
        return self.create_box(nu.get('header', 'Newsletter Updates'), self.make_urls_blue(text), 6.5*inch, self.body_text_large)

    def create_static_boxes(self):
        """Create the 3 static text boxes from JSON"""
        boxes = []
        static_boxes = self.static.get('static_boxes', {})
        width = 6.5*inch
        
        if static_boxes.get('box1'):
            boxes.append(self.create_box(None, self.clean_text(static_boxes['box1']), width, self.small_body))
        if static_boxes.get('box2'):
            boxes.append(self.create_box(None, self.clean_text(static_boxes['box2']), width, self.small_body))
        if static_boxes.get('box3'):
            box3_text = self.clean_text(static_boxes['box3']).replace('\n\n', '<br/><br/>')
            boxes.append(self.create_box(None, box3_text, width, self.small_body))
        
        return boxes

    def format_excomm_minutes(self):
        """Format ExComm minutes with proper indentation - returns content for box"""
        minutes_text = self.data.get('minutes', '')
        if not minutes_text:
            return []

        content_elements = []
        lines = self.clean_text(minutes_text).split('\n')

        # Header
        header_lines = []
        body_lines = []
        in_body = False

        for line in lines:
            if 'Meeting Convened' in line or 'meeting convened' in line.lower():
                in_body = True

            if not in_body:
                header_lines.append(line)
            else:
                body_lines.append(line)

        # Create header paragraph
        if header_lines:
            header_text = '<br/>'.join(header_lines)
            content_elements.append(Paragraph(header_text, self.minutes_header))
            content_elements.append(Spacer(1, 0.1*inch))

        # Process body with indentation
        for line in body_lines:
            if not line.strip():
                content_elements.append(Spacer(1, 0.05*inch))
                continue

            # Check if this is a special line that should be centered and italicized
            line_lower = line.strip().lower()
            is_special_line = any(keyword in line_lower for keyword in [
                'meeting convened', 'quorum established', 'meeting paused',
                'break', 'meeting adjourned'
            ])

            if is_special_line:
                # Left-align and italicize special lines
                styled_text = f"<i>{self.clean_text(line.strip())}</i>"
                style = ParagraphStyle('LeftItalic', parent=self.minutes_body,
                                      alignment=TA_LEFT)
                content_elements.append(Paragraph(styled_text, style))
            else:
                # Determine indentation level for regular lines
                indent = 0
                if line.strip().startswith('A.') or line.strip().startswith('B.') or \
                   line.strip().startswith('C.') or line.strip().startswith('D.') or \
                   line.strip().startswith('E.'):
                    indent = 20
                elif line.strip()[0:3] in ['I. ', 'II.', 'III', 'IV.', 'V. ']:
                    indent = 0
                elif not line.strip()[0].isdigit() and not line.strip().startswith('('):
                    indent = 40

                # Create paragraph with indentation
                style = ParagraphStyle('Indent', parent=self.minutes_body, leftIndent=indent)
                content_elements.append(Paragraph(self.clean_text(line), style))

        return content_elements

    def create_president_report(self):
        """Create President's Report"""
        for article in self.data.get('articles', []):
            if 'President' in article.get('title', ''):
                content = self.clean_text(article['content']).replace('\n', '<br/>')
                return self.create_box("President's Report", content, 6.5*inch, self.body_text_large)
        return []

    def create_officers_list(self):
        """Create officers list with dynamic header"""
        officers = self.data.get('officers', {})
        if not officers:
            return []

        # Get first calendar month for header
        calendar_months = self.config.get('calendar_months', [])
        if calendar_months:
            first_month = calendar_months[0]
            month_name = calendar.month_name[first_month['month']]
            year = first_month['year']
            header = f"Executive Committee of the Northwest Florida Mensa Local Group as of 1 {month_name} {year}"
        else:
            header = "Executive Committee of the Northwest Florida Mensa Local Group"

        # Create text listing: Position: Name with single line break
        lines = []
        for position, name in officers.items():
            lines.append(f"{position}: {name}<br/>")

        text = ''.join(lines).rstrip('<br/>')  # Remove trailing break

        return self.create_box(header, text, 6.5*inch, self.officers_style)

    def create_rc_columns(self):
        """Create RC10 columns with proper paragraph spacing"""
        story = []
        width = 6.5*inch
        
        # Across the Board October
        for article in self.data.get('articles', []):
            if 'October column' in article.get('title', ''):
                content = self.clean_text(article['content'])
                # Add double breaks at specific points
                content = content.replace('limitless!\nDon', 'limitless!<br/><br/>Don')
                content = content.replace('Region 10.\nHere', 'Region 10.<br/><br/>Here')
                content = content.replace('anyone?\n', 'anyone?<br/><br/>')
                content = content.replace('RC10@us.mensa.org\nMean', 'RC10@us.mensa.org<br/><br/>Mean')  # Replace specific email, not .org
                content = content.replace('\n', '<br/>')
                content = self.make_urls_blue(content)
                story.append(self.create_box("Across the Board (RC10 October column)",
                                           content, width, self.article_text))
                break
        
        # Across the Board September with image
        story.append(PageBreak())
        for article in self.data.get('articles', []):
            if 'September column' in article.get('title', ''):
                content = self.clean_text(article['content'])
                lines = content.split('\n')
                
                # First 3 lines full width
                first_lines = '<br/>'.join(lines[:3]) if len(lines) >= 3 else '<br/>'.join(lines)
                first_para = Paragraph(self.make_urls_blue(first_lines), self.article_text)
                
                # Rest with image
                if len(lines) > 3:
                    remaining_text = '<br/>'.join(lines[3:])
                    # Add double spacing
                    remaining_text = remaining_text.replace('anyone?', 'anyone?<br/><br/>')
                    remaining_text = remaining_text.replace('limitless!', 'limitless!<br/><br/>')
                    remaining_text = remaining_text.replace('Region 10.', 'Region 10.<br/><br/>')
                    remaining_text = remaining_text.replace('RC10@us.mensa.org', 'RC10@us.mensa.org<br/><br/>')  # Replace specific email, not .org
                    remaining_para = Paragraph(self.make_urls_blue(remaining_text), self.article_text)
                    
                    if os.path.exists('./1759079949624_image.jpg'):
                        img = Image('./1759079949624_image.jpg', 
                                  width=1.5*inch, height=2.5*inch)
                        content_table = Table([[img, remaining_para]], 
                                            colWidths=[1.7*inch, 4.8*inch])
                        content_table.setStyle(TableStyle([
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ]))
                        story.append(self.create_box("Across the Board (RC10 September column)", 
                                                   [first_para, content_table], width))
                    else:
                        story.append(self.create_box("Across the Board (RC10 September column)", 
                                                   [first_para, remaining_para], width))
                else:
                    story.append(self.create_box("Across the Board (RC10 September column)", 
                                               [first_para], width))
                break
        
        return story

    def create_event_sections(self):
        """Create event sections from JSON"""
        story = []
        width = 6.5*inch
        sections = self.static.get('event_sections', {})
        
        if not sections:
            return story
        
        # Regular Events
        if 'regular_events' in sections:
            re = sections['regular_events']
            text = self.clean_text(re.get('content', ''))
            story.append(self.create_box(re.get('header', 'Regular Events'), 
                                        self.make_urls_blue(text), width, self.body_text_left))
        
        # Wednesday Lunchers
        if 'wednesday_lunchers' in sections:
            wl = sections['wednesday_lunchers']
            text = self.clean_text(wl.get('content', '')).replace('\n', '<br/>')
            story.append(self.create_box(wl.get('header', 'Wednesday Lunchers'), 
                                        self.make_urls_blue(text), width, self.body_text_left))
        
        story.append(PageBreak())
        
        # Happy Hour
        if 'happy_hour' in sections:
            hh = sections['happy_hour']
            text = self.clean_text(hh.get('content', '')).replace('\n', '<br/>')
            story.append(self.create_box(hh.get('header', 'Happy Hour'), 
                                        self.make_urls_blue(text), width, self.body_text_left))
        
        # Panama City
        if 'panama_city' in sections:
            pc = sections['panama_city']
            text = self.clean_text(pc.get('content', '')).replace('\n', '<br/>')
            story.append(self.create_box(pc.get('header', 'Panama City Events'), 
                                        self.make_urls_blue(text), width, self.body_text_left))
        
        # Pensacola
        if 'pensacola' in sections:
            pe = sections['pensacola']
            text = self.clean_text(pe.get('content', '')).replace('\n', '<br/>')
            story.append(self.create_box(pe.get('header', 'Pensacola Events'), 
                                        self.make_urls_blue(text), width, self.body_text_left))
        
        # Cheers
        if 'cheers' in sections:
            ch = sections['cheers']
            text = self.clean_text(ch.get('content', '')).replace('\n', '<br/>')
            story.append(self.create_box(ch.get('header', 'Cheers!'), 
                                        self.make_urls_blue(text), width, self.body_text_left))
        
        # ExComm
        if 'excomm' in sections:
            ex = sections['excomm']
            text = self.clean_text(ex.get('content', '')).replace('\n', '<br/>')
            story.append(self.create_box(ex.get('header', 'ExComm'), 
                                        self.make_urls_blue(text), width, self.body_text_left))
        
        return story

    def create_weem_flyer(self):
        """Create WeeM flyer from JSON"""
        story = []
        width = 6.5*inch
        weem = self.static.get('weem', {})
        
        if not weem:
            return story
        
        # WeeM logo at top
        if os.path.exists('./1759081198901_image.png'):
            logo = Image('./1759081198901_image.png', width=4*inch, height=1*inch)
            story.append(logo)
            story.append(Spacer(1, 0.1*inch))
        
        # Header text
        header_style = ParagraphStyle('WeeM', parent=self.body_text, 
                                     alignment=TA_CENTER, leading=11)
        
        header_text = f"""<b>{weem.get('hosted', '')}<br/>
{weem.get('location', '')}<br/>
{weem.get('address', '')}</b>"""
        
        # Large tagline
        tagline = weem.get('tagline', '').replace('\n', '<br/>')
        big_text = f"""<font size="14"><b>{tagline}</b></font>"""
        
        content_parts = []
        content_parts.append(Paragraph(header_text, header_style))
        content_parts.append(Spacer(1, 0.1*inch))
        content_parts.append(Paragraph(big_text, ParagraphStyle('Big', parent=header_style, fontSize=14)))
        content_parts.append(Spacer(1, 0.1*inch))
        
        # Bullet points
        bullets_text = ""
        for bullet in weem.get('bullets', []):
            bullets_text += f"• {bullet}<br/>"
        bullets_text += f"<br/><b>{weem.get('price', '')}</b><br/>{weem.get('info', '')}"

        # Use left-aligned style for bullets
        bullets_style = ParagraphStyle('WeeMBullets', parent=self.body_text, alignment=TA_LEFT)
        bullets_para = Paragraph(self.make_urls_blue(bullets_text), bullets_style)
        
        # Add QR code if exists
        if os.path.exists('./1759081205215_image.jpg'):
            qr = Image('./1759081205215_image.jpg', width=1.5*inch, height=1.5*inch)
            content_table = Table([[bullets_para, qr]], 
                                colWidths=[4.5*inch, 2*inch])
            content_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            content_parts.append(content_table)
        else:
            content_parts.append(bullets_para)
        
        story.append(self.create_box(weem.get('header', 'WeeM 2025'), content_parts, width))
        
        return story

    def create_event_summary(self):
        """Create event summary without duplicate entries"""
        events = self.data.get('events', {})
        if not events:
            return []
            
        summary_lines = []
        
        for date in sorted(events.keys()):
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            date_str = date_obj.strftime('%b %-d')
            
            for event in events[date]:
                # Skip erroneous single-letter entries
                if event.get('title', '') in ['T', 'C']:
                    continue
                    
                parts = [date_str, event.get('time', ''), event.get('title', '')]
                if event.get('name'):
                    parts.append(self.clean_text(event['name']))
                if event.get('location'):
                    loc = self.clean_text(event['location']).replace('Fort Walton Beach', 'FWB')
                    parts.append(loc)
                if event.get('phone'):
                    parts.append(event['phone'])
                if event.get('url'):
                    parts.append(event['url'])
                    
                line = ', '.join(filter(None, parts))
                summary_lines.append(line)
        
        summary_text = '<br/>'.join(summary_lines)
        return self.create_box("Event Summary List", self.make_urls_blue(summary_text), 6.5*inch, self.tiny_text)

    def create_calendar(self, year, month):
        """Create calendar with better column widths and complete event display"""
        events = self.data.get('events', {})
        month_name = calendar.month_name[month]
        
        # Get first day of month
        first_weekday, num_days = calendar.monthrange(year, month)
        
        # Calculate starting position
        if first_weekday == 6:  # Sunday
            start_pos = 0
        else:
            start_pos = first_weekday + 1
        
        # Build calendar grid
        cal_grid = []
        week = [0] * 7
        day = 1
        
        # First week
        for pos in range(start_pos, 7):
            week[pos] = day
            day += 1
        cal_grid.append(week[:])
        
        # Remaining weeks
        while day <= num_days:
            week = []
            for _ in range(7):
                if day <= num_days:
                    week.append(day)
                    day += 1
                else:
                    week.append(0)
            cal_grid.append(week)
        
        # Calculate content density for better column widths
        col_content_count = [0] * 7
        for week in cal_grid:
            for col, day_num in enumerate(week):
                if day_num > 0:
                    date_key = f"{year}-{month:02d}-{day_num:02d}"
                    if date_key in events:
                        col_content_count[col] += len(events[date_key]) * 4
        
        # Dynamic column widths
        col_widths = []
        min_width = 0.6*inch
        max_width = 1.4*inch
        
        for col in range(7):
            if col_content_count[col] == 0:
                col_widths.append(min_width)
            elif col_content_count[col] > 8:
                col_widths.append(max_width)
            else:
                ratio = col_content_count[col] / 8
                col_widths.append(min_width + (max_width - min_width) * ratio)
        
        # Normalize to exactly 7.5 inches
        total = sum(col_widths)
        col_widths = [w * 7.5*inch / total for w in col_widths]
        
        # Banner
        banner = Table([[f"NW Florida Mensa Event Schedule for {month_name} {year}"]], 
                      colWidths=[7.5*inch], rowHeights=[0.3*inch])
        banner.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        # Days header
        days_table = Table([['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']], 
                          colWidths=col_widths, rowHeights=[0.25*inch])
        days_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.85, 0.85, 0.85)),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        
        # Calendar cells with complete event display
        cal_data = []
        for week in cal_grid:
            week_row = []
            for day_num in week:
                if day_num == 0:
                    week_row.append('')
                else:
                    date_key = f"{year}-{month:02d}-{day_num:02d}"
                    cell_lines = [f"<b>{day_num}</b>"]
                    
                    if date_key in events:
                        for evt in events[date_key][:2]:  # Show 2 events
                            # Skip erroneous entries
                            if evt.get('title', '') in ['T', 'C']:
                                continue
                                
                            cell_lines.append("")  # Blank line before event
                            
                            # Full event details
                            title = self.clean_text(evt.get('title', ''))
                            time = evt.get('time', '')
                            if time and title:
                                cell_lines.append(f"{time} - {title}"[:30])
                            
                            if evt.get('name'):
                                name = self.clean_text(evt['name'])
                                # Remove long parentheticals
                                if '(' in name and ')' in name:
                                    paren_content = name[name.find('(')+1:name.find(')')]
                                    if len(paren_content.split()) > 2:
                                        name = name[:name.find('(')].strip()
                                cell_lines.append(name[:28])
                            
                            if evt.get('location'):
                                loc = self.clean_text(evt['location'])
                                loc = loc.replace('Fort Walton Beach', 'FWB')
                                loc = loc.replace('Street', 'St')
                                loc = loc.replace('Parkway', 'Pkwy')
                                cell_lines.append(loc[:28])
                            
                            # Include URL if present
                            if evt.get('url'):
                                url = evt['url'].replace('https://', '').replace('http://', '')
                                if len(url) > 25:
                                    url = url[:22] + '...'
                                cell_lines.append(url)
                            elif evt.get('phone'):
                                cell_lines.append(evt['phone'])
                    
                    # Create paragraph with all lines
                    cell_text = '<br/>'.join(cell_lines[:10])
                    week_row.append(Paragraph(cell_text, self.cal_event_style))
            cal_data.append(week_row)
        
        # Calendar table
        cal_table = Table(cal_data, colWidths=col_widths, rowHeights=[1.2*inch]*len(cal_data))
        
        # Style
        styles = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
        ]
        
        # Gray empty cells
        for row_idx, week in enumerate(cal_grid):
            for col_idx, day in enumerate(week):
                if day == 0:
                    styles.append(('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx),
                                 colors.Color(0.9, 0.9, 0.9)))
        
        cal_table.setStyle(TableStyle(styles))
        
        return [banner, Spacer(1, 0.1*inch), days_table, cal_table]

    def generate(self, output_file):
        """Generate complete newsletter"""
        
        # Create document - main pages with 1" margins
        doc = SimpleDocTemplate(
            output_file,
            pagesize=letter,
            rightMargin=1*inch,
            leftMargin=1*inch,
            topMargin=1.25*inch,
            bottomMargin=1.25*inch
        )
        
        story = []
        width = 6.5*inch  # For regular pages with 1" margins
        
        # Page 1
        story.extend(self.create_page1())
        story.append(PageBreak())
        
        # Officers List
        officers = self.create_officers_list()
        if officers:
            story.append(officers)

        # ExComm Minutes
        minutes_content = self.format_excomm_minutes()
        if minutes_content:
            minutes_box = self.create_minutes_box("ExComm Meeting Minutes", minutes_content, width)
            story.append(minutes_box)
        
        # President's Report
        pr = self.create_president_report()
        if pr:
            story.append(pr)
        
        # Treasurer's Report
        tr = self.create_treasurer_report()
        if tr:
            story.append(tr)
        
        # Membership Statistics
        ms = self.create_membership_stats()
        if ms:
            story.append(ms)
        
        # Newsletter Updates
        nu = self.create_newsletter_updates()
        if nu:
            story.append(nu)
        
        # Static boxes
        static_boxes = self.create_static_boxes()
        for box in static_boxes:
            story.append(box)
        
        story.append(PageBreak())
        
        # RC Columns
        story.extend(self.create_rc_columns())
        
        # WeeM Flyer
        weem = self.create_weem_flyer()
        if weem:
            story.append(PageBreak())
            story.extend(weem)
        
        story.append(PageBreak())
        
        # Event sections
        story.extend(self.create_event_sections())
        
        # Event Summary
        summary = self.create_event_summary()
        if summary:
            story.append(PageBreak())
            story.append(summary)
        
        story.append(PageBreak())
        
        # Calendar pages (should use 0.5" margins but kept at 1" for now)
        for month_info in self.config.get('calendar_months', []):
            cal_elements = self.create_calendar(
                month_info['year'],
                month_info['month']
            )
            story.extend(cal_elements)
            if month_info != self.config['calendar_months'][-1]:
                story.append(PageBreak())
        
        # Build PDF
        doc.build(story, canvasmaker=PageNumCanvas)
        print(f"✅ Newsletter generated: {output_file}")

def main():
    """Main entry point with command-line argument handling"""
    
    # Parse command-line arguments
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        json_file = './pensa_mensa_content.json'
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        output_file = './newsletter.pdf'
    
    # Check if JSON file exists
    if not os.path.exists(json_file):
        print(f"❌ Error: JSON file '{json_file}' not found")
        print("\nUsage: python final_generator.py [json_file] [output_file]")
        print("Example: python final_generator.py ./data.json ./output.pdf")
        sys.exit(1)
    
    try:
        # Load JSON data
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        print(f"📄 Loaded data from: {json_file}")
        
        # Generate newsletter
        generator = NewsletterGenerator(data)
        generator.generate(output_file)
        
        print(f"✅ Success! Output saved to: {output_file}")
        
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in '{json_file}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error generating newsletter: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()