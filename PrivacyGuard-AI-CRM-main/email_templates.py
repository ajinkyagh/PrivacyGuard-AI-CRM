"""
Professional email templates for Luxury Automotive
"""

from datetime import datetime
from typing import Dict, List


def get_document_email_template(customer_name: str, document_types: List[str], vehicle_info: str = "") -> Dict[str, str]:
    """
    Generate a professional email template for sending documents
    
    Args:
        customer_name: Name of the customer
        document_types: List of document types being sent (e.g., ['quotation', 'invoice'])
        vehicle_info: Information about the vehicle (optional)
    
    Returns:
        Dict with 'subject' and 'body' keys
    """
    
    # Format document types for display
    if len(document_types) == 1:
        doc_description = document_types[0].title()
    elif len(document_types) == 2:
        doc_description = f"{document_types[0].title()} and {document_types[1].title()}"
    else:
        doc_description = ", ".join([doc.title() for doc in document_types[:-1]]) + f", and {document_types[-1].title()}"
    
    # Create subject line
    subject = f"Your {doc_description} - Luxury Automotive Experience"
    
    # Create email body
    body = f"""Dear {customer_name},

Greetings from Luxury Automotive!

We hope this email finds you well. Thank you for your interest in our premium luxury vehicle collection.

We are pleased to provide you with your requested {doc_description.lower()} as attached to this email. Our team has carefully prepared these documents to ensure all details are accurate and comprehensive.

Document Details:
"""
    
    # Add document descriptions
    for doc_type in document_types:
        if doc_type.lower() == 'quotation':
            body += f"• {doc_type.title()}: Detailed pricing and specifications for your selected vehicle\n"
        elif doc_type.lower() == 'invoice':
            body += f"• {doc_type.title()}: Official invoice with payment terms and conditions\n"
        elif doc_type.lower() == 'contract':
            body += f"• {doc_type.title()}: Purchase agreement with terms and conditions\n"
        else:
            body += f"• {doc_type.title()}: Important documentation for your reference\n"
    
    if vehicle_info:
        body += f"\nVehicle Information: {vehicle_info}\n"
    
    body += f"""
Please review the attached documents carefully. Should you have any questions or require clarification on any aspect, our dedicated team is here to assist you.

Next Steps:
• Review all attached documents thoroughly
• Contact us if you need any modifications or have questions
• Our luxury vehicle specialists are available for consultation
• We can arrange a private viewing or test drive at your convenience

Contact Information:
 Email: swanandvaidya2204@gmail.com
 Phone: Available during business hours
 Visit: Our premium showroom for personalized service

We appreciate your trust in Luxury Automotive and look forward to providing you with an exceptional luxury vehicle experience. Our commitment to excellence ensures that every aspect of your journey with us exceeds expectations.

Thank you for choosing Luxury Automotive  for your premium automotive needs.

Warm regards,

The Luxury Automotive Team
Luxury Automotive
"Excellence in Every Detail"

---
This email and any attachments are confidential and may be legally privileged. If you are not the intended recipient, please notify us immediately and delete this email.
"""
    
    # Create HTML version for better formatting
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background: linear-gradient(135deg, #1f2937, #374151); color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 30px; background: #f9fafb; }}
            .document-list {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3b82f6; }}
            .contact-info {{ background: #e5e7eb; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            .footer {{ background: #1f2937; color: white; padding: 20px; text-align: center; font-size: 12px; }}
            .highlight {{ color: #3b82f6; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Luxury Automotive</h1>
            <p>Excellence in Every Detail</p>
        </div>
        
        <div class="content">
            <h2>Dear {customer_name},</h2>
            
            <p>Greetings from <strong>Luxury Automotive</strong>!</p>
            
            <p>We hope this email finds you well. Thank you for your interest in our premium luxury vehicle collection.</p>
            
            <p>We are pleased to provide you with your requested <span class="highlight">{doc_description.lower()}</span> as attached to this email.</p>
            
            <div class="document-list">
                <h3>Document Details:</h3>
                <ul>
                    {"".join([f"<li><strong>{doc.title()}:</strong> Professional documentation for your reference</li>" for doc in document_types])}
                </ul>
                {f"<p><strong>Vehicle Information:</strong> {vehicle_info}</p>" if vehicle_info else ""}
            </div>
            
            <h3>Next Steps:</h3>
            <ul>
                <li>Review all attached documents thoroughly</li>
                <li>Contact us if you need any modifications or have questions</li>
                <li>Our luxury vehicle specialists are available for consultation</li>
            </ul>
            
            <div class="contact-info">
                <h3>📞Contact Information:</h3>
                <p><strong>Email:</strong> swanandvaidya2204@gmail.com<br>
                <strong>Phone:</strong> Available during business hours</p>
            </div>
            
            <p>Thank you for choosing <strong>Luxury Automotive</strong> for your premium automotive needs.</p>
            
            <p><strong>Warm regards,</strong><br>
            <strong>The Luxury Automotive Team</strong></p>
        </div>
        
        <div class="footer">
            <p>"Excellence in Every Detail"</p>
            <p><small>This email and any attachments are confidential and may be legally privileged.</small></p>
        </div>
    </body>
    </html>
    """
    
    return {
        "subject": subject,
        "body": body,
        "html_body": html_body
    }


def get_welcome_email_template(customer_name: str, vehicle_interest: str = "") -> Dict[str, str]:
    """
    Generate a professional welcome email template
    """
    subject = f"Welcome to Luxury Automotive - {customer_name}"
    
    body = f"""Dear {customer_name},

A warm welcome to Luxury Automotive!

Thank you for your interest in our exclusive collection of luxury vehicles. We are delighted to have you as our valued prospect and look forward to providing you with an unparalleled automotive experience.

At Luxury Automotive, we specialize in:
• Premium luxury vehicles from world-renowned brands
• Personalized consultation and expert guidance
• Exceptional customer service and support
• Comprehensive after-sales services

{f"We note your interest in {vehicle_interest} and our specialists will be in touch shortly to discuss your requirements in detail." if vehicle_interest else "Our team of luxury vehicle specialists will be in touch shortly to understand your preferences and requirements."}

What's Next:
1. Our specialist will contact you within 24 hours
2. Personalized consultation to understand your needs
3. Curated vehicle recommendations based on your preferences
4. Arrangement of private viewings and test drives

Contact Information:
Email: swanandvaidya2204@gmail.com
Phone: Available during business hours
Showroom: Premium location with exclusive inventory

We appreciate your trust in Luxury Automotive and are committed to making your luxury vehicle journey exceptional.

Best regards,

The Luxury Automotive Team
Luxury Automotive 
"Excellence in Every Detail"

---
This email is confidential. If received in error, please delete and notify us immediately.
"""
    
    return {
        "subject": subject,
        "body": body
    }


def get_followup_email_template(customer_name: str, context: str = "") -> Dict[str, str]:
    """
    Generate a professional follow-up email template
    """
    subject = f"Following Up on Your Luxury Vehicle Inquiry - {customer_name}"
    
    body = f"""Dear {customer_name},

I hope this email finds you well.

I wanted to personally follow up on your recent inquiry with Luxury Automotive . Your interest in our premium vehicle collection is greatly appreciated, and we want to ensure we're providing you with the exceptional service you deserve.

{context if context else "We understand that choosing a luxury vehicle is an important decision, and we're here to support you throughout the process."}

Our Commitment to You:
• Personalized attention from our luxury vehicle specialists
• Transparent and competitive pricing
• Comprehensive vehicle history and documentation
• Flexible financing and payment options
• Ongoing support and maintenance services

We would love to schedule a convenient time to discuss your requirements in detail or arrange a private viewing of vehicles that match your preferences.

Please feel free to reach out to us at your convenience:
Email: swanandvaidya2204@gmail.com
Phone: Available during business hours

Thank you for considering Luxury Automotive for your premium automotive needs. We look forward to hearing from you soon.

Warm regards,

The Luxury Automotive Team
Luxury Automotive 
"Excellence in Every Detail"
"""
    
    return {
        "subject": subject,
        "body": body
    }
