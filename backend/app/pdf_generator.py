"""PDF Generation Module for Lance AI Artifacts"""

import os
from datetime import datetime
from typing import Dict, Any, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT

class PDFGenerator:
    """Generate professional PDF documents for analysis artifacts"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Create custom paragraph styles for PDF"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Heading1 style
        self.styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=12,
            leftIndent=0
        ))
        
        # Heading2 style
        self.styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=8,
            spaceBefore=10
        ))
        
        # Body text style
        self.styles.add(ParagraphStyle(
            name='CustomBodyText',
            parent=self.styles['BodyText'],
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            leading=14
        ))
        
        # Quote style
        self.styles.add(ParagraphStyle(
            name='QuoteStyle',
            parent=self.styles['BodyText'],
            fontSize=10,
            leftIndent=20,
            rightIndent=20,
            textColor=colors.HexColor('#555555'),
            fontName='Helvetica-Oblique',
            borderColor=colors.HexColor('#cccccc'),
            borderWidth=1,
            borderPadding=10,
            spaceAfter=10
        ))
    
    def generate_hearing_pack_pdf(self, data: Dict[str, Any], output_path: str) -> str:
        """Generate PDF for hearing pack artifact"""
        doc = SimpleDocTemplate(output_path, pagesize=letter,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)
        
        story = []
        
        # Title
        story.append(Paragraph("Hearing Pack Documentation", self.styles['CustomTitle']))
        story.append(Spacer(1, 12))
        
        # Metadata
        story.append(Paragraph(f"<b>Session ID:</b> {data.get('session_id', 'N/A')}", self.styles['CustomBodyText']))
        story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", self.styles['CustomBodyText']))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        story.append(Spacer(1, 12))
        
        # Executive Summary
        if data.get('executive_summary'):
            story.append(Paragraph("Executive Summary", self.styles['CustomHeading1']))
            story.append(Paragraph(data['executive_summary'], self.styles['CustomBodyText']))
            story.append(Spacer(1, 12))
        
        # Coercive Control Analysis
        if data.get('coercive_control_analysis'):
            story.append(Paragraph("Coercive Control Analysis", self.styles['CustomHeading1']))
            analysis = data['coercive_control_analysis']
            
            if analysis.get('patterns'):
                story.append(Paragraph("Identified Patterns", self.styles['CustomHeading2']))
                for pattern in analysis['patterns']:
                    story.append(Paragraph(f"• <b>{pattern.get('type', 'Unknown')}:</b> {pattern.get('description', '')}", 
                                         self.styles['CustomBodyText']))
                story.append(Spacer(1, 8))
            
            if analysis.get('severity_score'):
                story.append(Paragraph(f"<b>Overall Severity Score:</b> {analysis['severity_score']}/10", 
                                     self.styles['CustomBodyText']))
                story.append(Spacer(1, 12))
        
        # Timeline of Events
        if data.get('timeline'):
            story.append(Paragraph("Timeline of Events", self.styles['CustomHeading1']))
            timeline_data = [['Date', 'Event', 'Evidence']]
            
            for event in data['timeline']:
                timeline_data.append([
                    event.get('date', 'N/A'),
                    event.get('description', ''),
                    event.get('evidence', '')[:50] + '...' if len(event.get('evidence', '')) > 50 else event.get('evidence', '')
                ])
            
            t = Table(timeline_data, colWidths=[1.5*inch, 3*inch, 2*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(t)
            story.append(Spacer(1, 12))
        
        # Evidence Summary
        if data.get('evidence_summary'):
            story.append(Paragraph("Evidence Summary", self.styles['CustomHeading1']))
            for evidence in data['evidence_summary']:
                story.append(Paragraph(f"<b>Document:</b> {evidence.get('doc_id', 'Unknown')}", 
                                     self.styles['CustomBodyText']))
                story.append(Paragraph(f"<i>\"{evidence.get('quote', '')}\"</i>", 
                                     self.styles['QuoteStyle']))
                story.append(Spacer(1, 6))
        
        # Recommendations
        if data.get('recommendations'):
            story.append(PageBreak())
            story.append(Paragraph("Recommendations", self.styles['CustomHeading1']))
            for i, rec in enumerate(data['recommendations'], 1):
                story.append(Paragraph(f"{i}. {rec}", self.styles['CustomBodyText']))
            story.append(Spacer(1, 12))
        
        # Build PDF
        doc.build(story)
        return output_path
    
    def generate_declaration_pdf(self, data: Dict[str, Any], output_path: str) -> str:
        """Generate PDF for declaration artifact"""
        doc = SimpleDocTemplate(output_path, pagesize=letter,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)
        
        story = []
        
        # Title
        story.append(Paragraph("Declaration", self.styles['CustomTitle']))
        story.append(Spacer(1, 12))
        
        # Declaration Header
        story.append(Paragraph(f"I, {data.get('declarant_name', '[Name]')}, declare under penalty of perjury under the laws of {data.get('jurisdiction', '[Jurisdiction]')} that the following is true and correct:",
                            self.styles['CustomBodyText']))
        story.append(Spacer(1, 12))
        
        # Declaration Points
        if data.get('declaration_points'):
            for i, point in enumerate(data['declaration_points'], 1):
                story.append(Paragraph(f"{i}. {point.get('statement', '')}", self.styles['CustomBodyText']))
                
                if point.get('supporting_evidence'):
                    story.append(Paragraph(f"<i>Supporting Evidence: {point['supporting_evidence']}</i>", 
                                         self.styles['QuoteStyle']))
                story.append(Spacer(1, 8))
        
        # Exhibits Section
        if data.get('exhibits'):
            story.append(PageBreak())
            story.append(Paragraph("Exhibits", self.styles['CustomHeading1']))
            
            exhibits_data = [['Exhibit', 'Description', 'Relevance']]
            for exhibit in data['exhibits']:
                exhibits_data.append([
                    exhibit.get('id', ''),
                    exhibit.get('description', ''),
                    exhibit.get('relevance', '')
                ])
            
            t = Table(exhibits_data, colWidths=[1*inch, 3*inch, 2.5*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(t)
        
        # Signature Block
        story.append(Spacer(1, 24))
        story.append(Paragraph("I declare under penalty of perjury that the foregoing is true and correct.", 
                             self.styles['CustomBodyText']))
        story.append(Spacer(1, 24))
        story.append(Paragraph(f"Executed on: {datetime.now().strftime('%B %d, %Y')}", 
                             self.styles['CustomBodyText']))
        story.append(Spacer(1, 12))
        story.append(Paragraph("_________________________________", self.styles['CustomBodyText']))
        story.append(Paragraph(data.get('declarant_name', '[Declarant Name]'), self.styles['CustomBodyText']))
        
        # Build PDF
        doc.build(story)
        return output_path
    
    def generate_client_letter_pdf(self, data: Dict[str, Any], output_path: str) -> str:
        """Generate PDF for client letter artifact"""
        doc = SimpleDocTemplate(output_path, pagesize=letter,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)
        
        story = []
        
        # Header
        story.append(Paragraph("Lance AI Legal Analysis", self.styles['CustomTitle']))
        story.append(Spacer(1, 6))
        story.append(Paragraph(datetime.now().strftime('%B %d, %Y'), self.styles['Normal']))
        story.append(Spacer(1, 24))
        
        # Salutation
        story.append(Paragraph(f"Dear {data.get('client_name', 'Client')},", self.styles['CustomBodyText']))
        story.append(Spacer(1, 12))
        
        # Introduction
        if data.get('introduction'):
            story.append(Paragraph(data['introduction'], self.styles['CustomBodyText']))
            story.append(Spacer(1, 12))
        
        # Case Assessment
        if data.get('case_assessment'):
            story.append(Paragraph("Case Assessment", self.styles['CustomHeading1']))
            story.append(Paragraph(data['case_assessment'], self.styles['CustomBodyText']))
            story.append(Spacer(1, 12))
        
        # Identified Issues
        if data.get('identified_issues'):
            story.append(Paragraph("Key Issues Identified", self.styles['CustomHeading1']))
            for issue in data['identified_issues']:
                story.append(Paragraph(f"• <b>{issue.get('title', '')}:</b> {issue.get('description', '')}", 
                                     self.styles['CustomBodyText']))
            story.append(Spacer(1, 12))
        
        # Recommended Actions
        if data.get('recommended_actions'):
            story.append(Paragraph("Recommended Next Steps", self.styles['CustomHeading1']))
            for i, action in enumerate(data['recommended_actions'], 1):
                story.append(Paragraph(f"{i}. <b>{action.get('action', '')}:</b> {action.get('rationale', '')}", 
                                     self.styles['CustomBodyText']))
            story.append(Spacer(1, 12))
        
        # Risks and Considerations
        if data.get('risks'):
            story.append(Paragraph("Important Considerations", self.styles['CustomHeading1']))
            for risk in data['risks']:
                story.append(Paragraph(f"• {risk}", self.styles['CustomBodyText']))
            story.append(Spacer(1, 12))
        
        # Closing
        if data.get('closing'):
            story.append(Paragraph(data['closing'], self.styles['CustomBodyText']))
        else:
            story.append(Paragraph("Please contact us if you have any questions or need clarification on any of these points. We are here to support you through this process.", 
                                 self.styles['CustomBodyText']))
        
        story.append(Spacer(1, 24))
        story.append(Paragraph("Sincerely,", self.styles['CustomBodyText']))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Lance AI Legal Team", self.styles['CustomBodyText']))
        
        # Disclaimer
        story.append(Spacer(1, 24))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        story.append(Spacer(1, 6))
        story.append(Paragraph("<i>This document was generated by Lance AI for informational purposes. Please consult with a licensed attorney for legal advice specific to your situation.</i>", 
                             self.styles['Normal']))
        
        # Build PDF
        doc.build(story)
        return output_path
    
    def generate_research_pdf(self, data: Dict[str, Any], output_path: str) -> str:
        """Generate PDF for research artifact"""
        doc = SimpleDocTemplate(output_path, pagesize=letter,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)
        
        story = []
        
        # Title
        story.append(Paragraph("Legal Research Summary", self.styles['CustomTitle']))
        story.append(Spacer(1, 12))
        
        # Metadata
        story.append(Paragraph(f"<b>Jurisdiction:</b> {data.get('jurisdiction', 'N/A')}", self.styles['CustomBodyText']))
        story.append(Paragraph(f"<b>Research Date:</b> {datetime.now().strftime('%B %d, %Y')}", self.styles['CustomBodyText']))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        story.append(Spacer(1, 12))
        
        # Executive Summary
        if data.get('summary'):
            story.append(Paragraph("Executive Summary", self.styles['CustomHeading1']))
            story.append(Paragraph(data['summary'], self.styles['CustomBodyText']))
            story.append(Spacer(1, 12))
        
        # Statutes
        if data.get('authorities'):
            statutes = [auth for auth in data['authorities'] if auth.get('type') == 'statute']
            if statutes:
                story.append(Paragraph("Relevant Statutes", self.styles['CustomHeading1']))
                for statute in statutes:
                    story.append(Paragraph(f"<b>{statute.get('citation', '')}</b>", self.styles['CustomBodyText']))
                    story.append(Paragraph(f"<i>\"{statute.get('quote', '')}\"</i>", self.styles['QuoteStyle']))
                    story.append(Paragraph(f"Relevance: {statute.get('relevance', '')}", self.styles['CustomBodyText']))
                    if statute.get('url'):
                        story.append(Paragraph(f"<link href='{statute['url']}'>View Source</link>", 
                                             self.styles['CustomBodyText']))
                    story.append(Spacer(1, 12))
        
        # Case Law
        if data.get('authorities'):
            cases = [auth for auth in data['authorities'] if auth.get('type') == 'case']
            if cases:
                story.append(Paragraph("Relevant Case Law", self.styles['CustomHeading1']))
                for case in cases:
                    story.append(Paragraph(f"<b>{case.get('citation', '')}</b>", self.styles['CustomBodyText']))
                    story.append(Paragraph(f"<i>\"{case.get('quote', '')}\"</i>", self.styles['QuoteStyle']))
                    story.append(Paragraph(f"Relevance: {case.get('relevance', '')}", self.styles['CustomBodyText']))
                    story.append(Spacer(1, 12))
        
        # Web Sources
        if data.get('web_sources'):
            story.append(PageBreak())
            story.append(Paragraph("Additional Web Resources", self.styles['CustomHeading1']))
            for source in data['web_sources'][:5]:
                story.append(Paragraph(f"<b>{source.get('title', '')}</b>", self.styles['CustomBodyText']))
                story.append(Paragraph(f"<link href='{source.get('url', '')}'>Link</link>", 
                                     self.styles['CustomBodyText']))
                story.append(Paragraph(source.get('content', '')[:200] + '...', self.styles['CustomBodyText']))
                story.append(Spacer(1, 8))
        
        # Build PDF
        doc.build(story)
        return output_path
    
    def generate_analysis_summary_pdf(self, data: Dict[str, Any], output_path: str) -> str:
        """Generate PDF for analysis summary artifact"""
        doc = SimpleDocTemplate(output_path, pagesize=letter,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)
        
        story = []
        
        # Title
        story.append(Paragraph("Comprehensive Analysis Summary", self.styles['CustomTitle']))
        story.append(Spacer(1, 12))
        
        # Executive Overview
        if data.get('executive_overview'):
            story.append(Paragraph("Executive Overview", self.styles['CustomHeading1']))
            story.append(Paragraph(data['executive_overview'], self.styles['CustomBodyText']))
            story.append(Spacer(1, 12))
        
        # Quality Assessment
        if data.get('quality_metrics'):
            story.append(Paragraph("Quality Assessment", self.styles['CustomHeading1']))
            metrics = data['quality_metrics']
            
            metrics_data = [['Metric', 'Score', 'Status']]
            if metrics.get('completeness_score'):
                metrics_data.append(['Completeness', f"{metrics['completeness_score']}%", 
                                    'Pass' if metrics['completeness_score'] >= 80 else 'Review'])
            if metrics.get('accuracy_score'):
                metrics_data.append(['Accuracy', f"{metrics['accuracy_score']}%",
                                    'Pass' if metrics['accuracy_score'] >= 85 else 'Review'])
            if metrics.get('coherence_score'):
                metrics_data.append(['Coherence', f"{metrics['coherence_score']}%",
                                    'Pass' if metrics['coherence_score'] >= 80 else 'Review'])
            
            if len(metrics_data) > 1:
                t = Table(metrics_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(t)
                story.append(Spacer(1, 12))
        
        # Key Findings
        if data.get('key_findings'):
            story.append(Paragraph("Key Findings", self.styles['CustomHeading1']))
            for finding in data['key_findings']:
                story.append(Paragraph(f"• {finding}", self.styles['CustomBodyText']))
            story.append(Spacer(1, 12))
        
        # Recommendations
        if data.get('recommendations'):
            story.append(Paragraph("Strategic Recommendations", self.styles['CustomHeading1']))
            for i, rec in enumerate(data['recommendations'], 1):
                story.append(Paragraph(f"{i}. {rec}", self.styles['CustomBodyText']))
            story.append(Spacer(1, 12))
        
        # Next Steps
        if data.get('next_steps'):
            story.append(Paragraph("Immediate Next Steps", self.styles['CustomHeading1']))
            for step in data['next_steps']:
                story.append(Paragraph(f"□ {step}", self.styles['CustomBodyText']))
        
        # Build PDF
        doc.build(story)
        return output_path
