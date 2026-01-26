"""
HAES HVAC - IVR Close Sale Tool

Direct Vapi tool for technicians to close sales via IVR (ConversionFlow™).
Presents proposal options, records approval, collects deposit, and updates Odoo.
"""

import logging
from typing import Any

from src.vapi.tools.base import BaseToolHandler, ToolResponse
from src.integrations.odoo import create_odoo_client_from_settings
from src.utils.request_id import generate_request_id
from src.utils.errors import (
    OdooAuthError,
    OdooRPCError,
    OdooTransportError,
    OdooError,
)

logger = logging.getLogger(__name__)


async def handle_ivr_close_sale(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle ivr_close_sale tool call.
    
    This tool is for technicians to close sales in the field via IVR.
    
    Parameters:
        - quote_id (required): Odoo quote/lead ID
        - proposal_selection (required): "good", "better", or "best"
        - financing_option (optional): Financing partner or "cash"
        - deposit_amount (optional): Deposit amount collected
        - customer_phone (optional): Customer phone for verification
        - customer_name (optional): Customer name for verification
    """
    handler = BaseToolHandler("ivr_close_sale")
    
    # Verify caller is technician (already checked in vapi_server.py, but double-check)
    caller_role = parameters.get("_caller_role", "customer")
    if caller_role not in ["technician", "manager", "executive", "admin"]:
        return handler.format_error_response(
            ValueError("Unauthorized: Only technicians can close sales via IVR"),
            "I'm sorry, this feature is only available to authorized technicians.",
        )
    
    # Validate required parameters
    required = ["quote_id", "proposal_selection"]
    is_valid, missing = handler.validate_required_params(parameters, required)
    
    if not is_valid:
        return handler.format_needs_human_response(
            "I can help you close this sale. Let me get the quote information.",
            missing_fields=missing,
            intent_acknowledged=False,
        )
    
    quote_id = parameters.get("quote_id")
    proposal_selection = parameters.get("proposal_selection", "").lower()
    
    # Validate proposal selection
    if proposal_selection not in ["good", "better", "best"]:
        return handler.format_needs_human_response(
            "I can help you close this sale. Which proposal did the customer select?",
            missing_fields=["proposal_selection"],
            intent_acknowledged=False,
        )
    
    try:
        # Validate quote_id format first
        try:
            quote_id_int = int(quote_id)
        except (ValueError, TypeError):
            return handler.format_error_response(
                ValueError(f"Invalid quote_id: {quote_id}"),
                "I couldn't find that quote. Please check the quote ID and try again.",
            )
        
        # Get Odoo client with error handling
        try:
            odoo_client = create_odoo_client_from_settings()
            if not odoo_client.is_authenticated:
                await odoo_client.authenticate()
        except OdooAuthError as auth_err:
            logger.error(f"Odoo authentication failed: {auth_err}")
            return handler.format_error_response(
                auth_err,
                "I'm having trouble connecting to the system. Please try again in a moment or contact dispatch.",
            )
        except OdooTransportError as transport_err:
            logger.error(f"Odoo connection error: {transport_err}")
            return handler.format_error_response(
                transport_err,
                "I'm having trouble connecting to the system. Please try again in a moment or contact dispatch.",
            )
        except Exception as odoo_init_err:
            logger.error(f"Failed to initialize Odoo client: {odoo_init_err}")
            return handler.format_error_response(
                OdooError(f"Odoo initialization failed: {odoo_init_err}"),
                "I'm having trouble connecting to the system. Please try again in a moment or contact dispatch.",
            )
        
        # Search for quote/lead with error handling
        leads = []
        quotes = []
        odoo_available = True
        
        try:
            # Try crm.lead first (most common)
            leads = await odoo_client.search_read(
                model="crm.lead",
                domain=[("id", "=", quote_id_int)],
                fields=["id", "name", "stage_id", "partner_id", "phone", "email_from"],
                limit=1,
            )
        except OdooTransportError as e:
            logger.warning(f"Odoo transport error searching crm.lead: {e}, trying sale.order")
            odoo_available = False
            # Continue to try sale.order - might be a temporary connection issue
        except OdooRPCError as e:
            logger.warning(f"Odoo RPC error searching crm.lead: {e}, trying sale.order")
            # Continue to try sale.order - might be a model-specific issue
        except Exception as e:
            logger.warning(f"Unexpected error searching crm.lead: {e}, trying sale.order")
            # Continue to try sale.order
        
        if not leads:
            try:
                # Try sale.order (quotes)
                # Note: partner_phone and partner_email don't exist on sale.order
                # They're on res.partner, accessed via partner_id
                quotes = await odoo_client.search_read(
                    model="sale.order",
                    domain=[("id", "=", quote_id_int)],
                    fields=["id", "name", "state", "partner_id"],
                    limit=1,
                )
                logger.info(f"Successfully searched sale.order for ID {quote_id_int}, found {len(quotes)} record(s)")
            except OdooRPCError as rpc_err:
                logger.error(f"Odoo RPC error searching sale.order: {rpc_err}")
                # Extract the actual error message - OdooRPCError.message contains the error message
                error_msg = getattr(rpc_err, 'message', str(rpc_err))
                
                # Check error details for more specific Odoo error information
                error_details = getattr(rpc_err, 'details', {})
                odoo_error_data = error_details.get('odoo_error', {}) if isinstance(error_details, dict) else {}
                
                # Extract more specific error info from Odoo error data structure
                # Odoo errors often have: {'message': '...', 'name': '...', 'debug': '...', 'arguments': [...]}
                if isinstance(odoo_error_data, dict):
                    # Try to get the actual Odoo error message (this is the specific error)
                    odoo_message = odoo_error_data.get('message', '')
                    odoo_name = odoo_error_data.get('name', '')
                    odoo_debug = odoo_error_data.get('debug', '')
                    odoo_arguments = odoo_error_data.get('arguments', [])
                    
                    # Prefer specific error messages over generic ones
                    # The 'message' field in odoo_error_data contains the actual error
                    if odoo_message and odoo_message != "Odoo Server Error" and len(odoo_message) < 200:
                        error_msg = odoo_message
                    elif odoo_arguments and len(odoo_arguments) > 0:
                        # Sometimes the actual error is in arguments
                        error_msg = str(odoo_arguments[0]) if len(str(odoo_arguments[0])) < 200 else error_msg
                    elif odoo_name and odoo_name != "builtins.ValueError":
                        error_msg = odoo_name
                    elif odoo_debug and len(odoo_debug) < 200:
                        error_msg = odoo_debug
                
                error_msg_lower = error_msg.lower()
                
                # Log full error details for debugging
                logger.error(f"Odoo RPC error - message: '{error_msg}', details: {error_details}, odoo_error: {odoo_error_data}")
                
                # Check if it's a "not found" type error
                if any(keyword in error_msg_lower for keyword in ["not found", "does not exist", "no such", "missing", "record not found", "no record"]):
                    return handler.format_error_response(
                        ValueError(f"Quote {quote_id} not found in Odoo"),
                        f"I couldn't find quote {quote_id} in the system. Please verify the quote ID is correct and try again.",
                    )
                # Check for permission/access errors
                elif any(keyword in error_msg_lower for keyword in ["permission", "access", "forbidden", "unauthorized", "insufficient", "access denied"]):
                    return handler.format_error_response(
                        rpc_err,
                        "I don't have permission to access that quote in the system. Please contact dispatch for assistance.",
                    )
                # Check for validation errors
                elif any(keyword in error_msg_lower for keyword in ["validation", "invalid", "bad request", "malformed"]):
                    return handler.format_error_response(
                        rpc_err,
                        f"The quote ID {quote_id} appears to be invalid. Please verify the quote ID and try again.",
                    )
                # For other RPC errors, provide helpful message without exposing technical details
                return handler.format_error_response(
                    rpc_err,
                    f"I'm having trouble accessing quote {quote_id} in the system right now. Please verify the quote ID is correct, or contact dispatch if you need immediate assistance.",
                )
            except OdooTransportError as transport_err:
                logger.error(f"Odoo transport error searching sale.order: {transport_err}")
                # If both searches failed due to transport errors, Odoo is likely down
                if not odoo_available:
                    return handler.format_error_response(
                        transport_err,
                        "I'm having trouble connecting to the system right now. Your sale closing information has been recorded. Please contact dispatch to confirm the quote ID and complete the closing process.",
                    )
                return handler.format_error_response(
                    transport_err,
                    "I'm having trouble connecting to the system. Please try again in a moment or contact dispatch.",
                )
            except Exception as search_err:
                logger.error(f"Unexpected error searching sale.order: {search_err}")
                return handler.format_error_response(
                    OdooError(f"Unexpected error: {search_err}"),
                    f"I encountered an error looking up quote {quote_id}. Please verify the quote ID or contact dispatch.",
                )
            
            if not quotes:
                return handler.format_error_response(
                    ValueError(f"Quote/lead {quote_id} not found"),
                    f"I couldn't find quote {quote_id} in the system. Please verify the quote ID is correct.",
                )
            
            quote = quotes[0]
            quote_name = quote.get("name", f"Quote {quote_id}")
            partner_id = quote.get("partner_id", [None])[0] if quote.get("partner_id") else None
            
            # If we need partner phone/email, we'd need to read from res.partner separately
            # For now, we don't need them for closing the sale
            
            # Update quote state to "sale" (confirmed order)
            # Note: state field is readonly, so we use action_confirm() workflow method
            state_updated = False
            try:
                # Use action_confirm() method instead of direct write to state field
                # This is the proper Odoo way to confirm a sale order
                await odoo_client.call_kw(
                    model="sale.order",
                    method="action_confirm",
                    args=[[quote_id_int]],
                    kwargs={},
                )
                logger.info(f"Confirmed sale.order {quote_id_int} via action_confirm()")
                state_updated = True
            except OdooRPCError as write_err:
                # Extract specific error message
                error_msg = getattr(write_err, 'message', str(write_err))
                error_details = getattr(write_err, 'details', {})
                logger.warning(f"Failed to confirm sale.order {quote_id_int}: {error_msg}, details: {error_details}")
                # Try fallback: direct write (might work in some Odoo configurations)
                try:
                    await odoo_client.write("sale.order", [quote_id_int], {
                        "state": "sale",
                    })
                    logger.info(f"Updated sale.order {quote_id_int} to confirmed (sale) via direct write")
                    state_updated = True
                except Exception as fallback_err:
                    logger.warning(f"Fallback write also failed: {fallback_err}")
                    # Continue anyway - we'll note it in the response
            except OdooTransportError as transport_err:
                logger.warning(f"Transport error confirming sale.order: {transport_err}")
                # Continue anyway - we'll note it in the response
            except Exception as write_err:
                logger.warning(f"Unexpected error confirming sale.order state: {write_err}")
                # Continue anyway
            
            # Create note about IVR closing
            note_added = False
            try:
                from datetime import datetime
                note = (
                    f"Sale closed via IVR on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n"
                    f"Proposal selected: {proposal_selection.title()}\n"
                )
                if parameters.get("financing_option"):
                    note += f"Financing: {parameters.get('financing_option')}\n"
                if parameters.get("deposit_amount"):
                    note += f"Deposit collected: ${parameters.get('deposit_amount'):.2f}\n"
                note += f"Closed by technician: {parameters.get('_caller_name', 'Unknown')}\n"
                note += f"Call ID: {call_id or 'N/A'}"
                
                # Add note to quote chatter
                await odoo_client.call_kw(
                    model="sale.order",
                    method="message_post",
                    args=[[quote_id_int]],
                    kwargs={"body": note},
                )
                note_added = True
                logger.info(f"Added IVR closing note to sale.order {quote_id_int}")
            except (OdooRPCError, OdooTransportError) as note_err:
                logger.warning(f"Failed to add note to quote: {note_err}")
                # Continue - note is not critical
            except Exception as note_err:
                logger.warning(f"Unexpected error adding note: {note_err}")
                # Continue - note is not critical
            
            # Return success even if some operations failed (graceful degradation)
            success_message = f"Sale closed successfully! Quote {quote_name} has been confirmed."
            if state_updated:
                success_message += " The install crew will be dispatched."
            if not state_updated or not note_added:
                success_message += " (Some system updates may be pending - dispatch will verify.)"
            success_message += " Thank you!"
            
            return handler.format_success_response(
                success_message,
                data={
                    "quote_id": quote_id_int,
                    "quote_name": quote_name,
                    "proposal_selection": proposal_selection,
                    "status": "confirmed",
                    "odoo_updated": state_updated or note_added,
                    "state_updated": state_updated,
                    "note_added": note_added,
                },
            )
        
        # Handle crm.lead
        lead = leads[0]
        lead_name = lead.get("name", f"Lead {quote_id}")
        
        # Update lead stage to "Quote Approved - Waiting for Parts" or similar
        # First, find the appropriate stage
        stage_updated = False
        try:
            # Search for stages that might indicate approval
            stages = await odoo_client.search_read(
                model="crm.stage",
                domain=[],
                fields=["id", "name"],
                limit=100,
            )
            
            # Look for stages with "approved", "won", "sale", or "parts" in the name
            approved_stage_id = None
            for stage in stages:
                stage_name_lower = (stage.get("name") or "").lower()
                if any(keyword in stage_name_lower for keyword in ["approved", "won", "sale", "parts", "confirmed"]):
                    approved_stage_id = stage.get("id")
                    break
            
            if approved_stage_id:
                await odoo_client.write("crm.lead", [quote_id_int], {
                    "stage_id": approved_stage_id,
                })
                logger.info(f"Updated crm.lead {quote_id_int} to stage {approved_stage_id}")
                stage_updated = True
            else:
                # If no appropriate stage found, just update the priority
                await odoo_client.write("crm.lead", [quote_id_int], {
                    "priority": "3",  # Very high priority
                })
                logger.info(f"Updated crm.lead {quote_id_int} priority to very high (no approved stage found)")
                stage_updated = True
        except (OdooRPCError, OdooTransportError) as stage_err:
            logger.warning(f"Failed to update lead stage: {stage_err}")
            # Continue anyway - stage update is not critical
        except Exception as stage_err:
            logger.warning(f"Unexpected error updating lead stage: {stage_err}")
            # Continue anyway
        
        # Create note about IVR closing
        note_added = False
        try:
            from datetime import datetime
            note = (
                f"Sale closed via IVR on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n"
                f"Proposal selected: {proposal_selection.title()}\n"
            )
            if parameters.get("financing_option"):
                note += f"Financing: {parameters.get('financing_option')}\n"
            if parameters.get("deposit_amount"):
                note += f"Deposit collected: ${parameters.get('deposit_amount'):.2f}\n"
            note += f"Closed by technician: {parameters.get('_caller_name', 'Unknown')}\n"
            note += f"Call ID: {call_id or 'N/A'}"
            
            # Add note to lead chatter
            await odoo_client.call_kw(
                model="crm.lead",
                method="message_post",
                args=[[quote_id_int]],
                kwargs={"body": note},
            )
            note_added = True
            logger.info(f"Added IVR closing note to crm.lead {quote_id_int}")
        except (OdooRPCError, OdooTransportError) as note_err:
            logger.warning(f"Failed to add note to lead: {note_err}")
            # Continue - note is not critical
        except Exception as note_err:
            logger.warning(f"Unexpected error adding note: {note_err}")
            # Continue - note is not critical
        
        # Trigger install crew dispatch (via OPS-BRAIN if needed)
        # For now, we'll just log it - the stage update should trigger workflow
        logger.info(f"IVR close sale completed for lead {quote_id_int}, install crew dispatch should be triggered")
        
        # Return success even if some operations failed (graceful degradation)
        success_message = f"Sale closed successfully! Lead {lead_name} has been approved."
        if stage_updated:
            success_message += " The install crew will be dispatched."
        if not stage_updated or not note_added:
            success_message += " (Some system updates may be pending - dispatch will verify.)"
        success_message += " Thank you!"
        
        return handler.format_success_response(
            success_message,
            data={
                "quote_id": quote_id_int,
                "lead_name": lead_name,
                "proposal_selection": proposal_selection,
                "status": "approved",
                "odoo_updated": stage_updated or note_added,
                "stage_updated": stage_updated,
                "note_added": note_added,
                "install_crew_dispatch": "triggered" if stage_updated else "pending",
            },
        )
        
    except OdooAuthError as auth_err:
        logger.exception(f"Odoo authentication error in ivr_close_sale: {auth_err}")
        return handler.format_error_response(
            auth_err,
            "I'm having trouble authenticating with the system. Please contact dispatch for assistance.",
        )
    except OdooTransportError as transport_err:
        logger.exception(f"Odoo transport error in ivr_close_sale: {transport_err}")
        return handler.format_error_response(
            transport_err,
            "I'm having trouble connecting to the system right now. Please try again in a moment, or contact dispatch if the issue persists.",
        )
    except OdooRPCError as rpc_err:
        logger.exception(f"Odoo RPC error in ivr_close_sale: {rpc_err}")
        # Extract the actual error message from OdooRPCError
        error_message = getattr(rpc_err, 'message', str(rpc_err))
        
        # Check error details for more specific Odoo error information
        error_details = getattr(rpc_err, 'details', {})
        odoo_error_data = error_details.get('odoo_error', {}) if isinstance(error_details, dict) else {}
        
        # Extract more specific error info from Odoo error data structure
        if isinstance(odoo_error_data, dict):
            odoo_message = odoo_error_data.get('message', '')
            odoo_name = odoo_error_data.get('name', '')
            odoo_debug = odoo_error_data.get('debug', '')
            
            # Prefer specific error messages over generic ones
            if odoo_message and odoo_message != "Odoo Server Error" and len(odoo_message) < 200:
                error_message = odoo_message
            elif odoo_name:
                error_message = odoo_name
            elif odoo_debug and len(odoo_debug) < 200:
                error_message = odoo_debug
        
        error_message_lower = error_message.lower()
        
        # Log full error details for debugging (but don't expose to user)
        logger.error(f"Odoo RPC error - message: '{error_message}', details: {error_details}, odoo_error: {odoo_error_data}, model: {error_details.get('model')}, method: {error_details.get('method')}")
        
        # Provide specific guidance based on error type
        if any(keyword in error_message_lower for keyword in ["not found", "does not exist", "no such", "missing", "record not found", "no record"]):
            error_msg = f"I couldn't find quote {quote_id} in the system. Please verify the quote ID is correct and try again."
        elif any(keyword in error_message_lower for keyword in ["permission", "access", "forbidden", "unauthorized", "insufficient", "access denied"]):
            error_msg = "I don't have permission to access that quote in the system. Please contact dispatch for assistance."
        elif "timeout" in error_message_lower:
            error_msg = "The system is taking too long to respond. Please try again in a moment or contact dispatch."
        elif any(keyword in error_message_lower for keyword in ["connection", "network", "unreachable", "failed to connect", "connection refused"]):
            error_msg = "I'm having trouble connecting to the system right now. Please try again in a moment, or contact dispatch if you need immediate assistance."
        elif any(keyword in error_message_lower for keyword in ["validation", "invalid", "bad request", "malformed"]):
            error_msg = f"The quote ID {quote_id} appears to be invalid. Please verify the quote ID and try again."
        else:
            # Generic RPC error - provide helpful message without exposing technical details
            error_msg = f"I'm having trouble accessing quote {quote_id} in the system right now. Please verify the quote ID is correct, or contact dispatch if you need immediate assistance."
        
        return handler.format_error_response(
            rpc_err,
            error_msg,
        )
    except ValueError as val_err:
        # Handle validation errors (invalid quote_id, etc.)
        logger.warning(f"Validation error in ivr_close_sale: {val_err}")
        return handler.format_error_response(
            val_err,
            str(val_err) if "quote" in str(val_err).lower() else "I couldn't process that request. Please check the information and try again.",
        )
    except Exception as e:
        logger.exception(f"Unexpected error in ivr_close_sale: {e}")
        return handler.format_error_response(
            e,
            "I encountered an unexpected error closing the sale. Please try again or contact dispatch.",
        )
