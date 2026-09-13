import json
from django.conf import settings
from django.db.models import Q
from openai import OpenAI
from .models import Delivery, SurplusFood, OrganizationImpact, Organization

def get_active_deliveries(organization_id: int):
    """Fetch active deliveries for an organization."""
    try:
        org = Organization.objects.get(id=organization_id)
        deliveries = Delivery.objects.filter(
            Q(sender=org) | Q(receiver=org)
        ).exclude(status__in=["DELIVERED", "CANCELLED"])
        
        data = []
        for d in deliveries:
            data.append({
                "tracking_code": d.tracking_code,
                "food": d.food_name,
                "quantity": d.quantity,
                "status": d.status,
                "driver": d.driver_name or "Unassigned"
            })
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_surplus_inventory():
    """Fetch available surplus food."""
    try:
        surplus = SurplusFood.objects.filter(status="SAFE")
        data = []
        for s in surplus:
            data.append({
                "food": s.food_name,
                "quantity": s.quantity,
                "organization": s.organization.name,
                "location": s.organization.city or "Unknown"
            })
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_impact_score(organization_id: int):
    """Fetch the impact score of an organization."""
    try:
        org = Organization.objects.get(id=organization_id)
        impact = OrganizationImpact.objects.filter(organization=org).first()
        if impact:
            return json.dumps({
                "points": impact.points,
                "rank_title": impact.rank_title
            })
        return json.dumps({"points": 0, "rank_title": "Bronze"})
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_live_weather(city: str):
    """Fetch live weather data for a city."""
    try:
        from .views import _weather
        weather_data = _weather(city)
        if weather_data:
            return json.dumps(weather_data)
        return json.dumps({"error": "Weather data unavailable or API key not set."})
    except Exception as e:
        return json.dumps({"error": str(e)})

def predict_food_demand(attendance: int, temperature: float = 25.0, rainfall: float = 0.0, holiday: int = 0, humidity: float = 70.0, exam_day: int = 0, event_flag: int = 0):
    """Predict food demand using the ML model."""
    try:
        from .views import _predict
        result = _predict(
            attendance=attendance,
            temperature=temperature,
            rainfall=rainfall,
            holiday=holiday,
            humidity=humidity,
            exam_day=exam_day,
            event_flag=event_flag
        )
        if result:
            return json.dumps(result)
        return json.dumps({"error": "Prediction model unavailable."})
    except Exception as e:
        return json.dumps({"error": str(e)})


def generate_copilot_response(user_message: str, organization: Organization) -> str:
    """
    Calls the OpenAI API to generate a response for the AgroFedly Copilot,
    with advanced function calling.
    """
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return "System configuration error: OPENAI_API_KEY is not set."

    client = OpenAI(api_key=api_key)

    system_prompt = f"""
    You are the AgroFedly AI Copilot. You are a helpful, professional assistant integrated into a food surplus distribution and agriculture management app.
    Your main responsibilities include:
    - Helping organizations understand how to donate surplus food.
    - Providing updates on food deliveries.
    - Advising on food safety guidelines (e.g. storage temperatures).
    - Guiding volunteers on how they can help drive and redistribute food.
    
    You have tools to fetch real-time data from the database. Use them when the user asks about deliveries, surplus, or impact scores.
    The user asking the question belongs to the organization: {organization.name} (ID: {organization.id}).
    Always summarize tool responses nicely. Keep your answers concise, friendly, and practical.
    """
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_active_deliveries",
                "description": "Fetch a list of active/pending deliveries for the current organization. Use this when the user asks about their deliveries, shipments, or tracking.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "organization_id": {
                            "type": "integer",
                            "description": "The ID of the organization. Must be the logged-in user's organization ID."
                        }
                    },
                    "required": ["organization_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_surplus_inventory",
                "description": "Fetch a list of all currently available surplus food items from all organizations that are marked as safe for consumption. Use this when the user asks what food is available to claim.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_impact_score",
                "description": "Fetch the gamification impact score and rank of the organization.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "organization_id": {
                            "type": "integer",
                            "description": "The ID of the organization. Must be the logged-in user's organization ID."
                        }
                    },
                    "required": ["organization_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_live_weather",
                "description": "Fetch live weather data for a specified city.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "The name of the city, e.g., 'London' or 'New York'."
                        }
                    },
                    "required": ["city"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "predict_food_demand",
                "description": "Predict the food demand using a machine learning model based on various environmental and event factors.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "attendance": {
                            "type": "integer",
                            "description": "The expected number of students or attendees."
                        },
                        "temperature": {
                            "type": "number",
                            "description": "The expected temperature in Celsius. Default is 25.0."
                        },
                        "rainfall": {
                            "type": "number",
                            "description": "The expected rainfall in mm. Default is 0.0."
                        },
                        "holiday": {
                            "type": "integer",
                            "description": "Whether it is a holiday (1 for yes, 0 for no). Default is 0."
                        },
                        "humidity": {
                            "type": "number",
                            "description": "The expected humidity percentage. Default is 70.0."
                        },
                        "exam_day": {
                            "type": "integer",
                            "description": "Whether it is an exam day (1 for yes, 0 for no). Default is 0."
                        },
                        "event_flag": {
                            "type": "integer",
                            "description": "Whether there is a special event (1 for yes, 0 for no). Default is 0."
                        }
                    },
                    "required": ["attendance"]
                }
            }
        }
    ]

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=300
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        if tool_calls:
            # Append the assistant's message containing the tool calls
            messages.append(response_message)
            
            # Execute tools
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                function_response = ""
                
                if function_name == "get_active_deliveries":
                    # Security override: force the user's organization ID
                    function_response = get_active_deliveries(organization.id)
                elif function_name == "get_surplus_inventory":
                    function_response = get_surplus_inventory()
                elif function_name == "get_impact_score":
                    # Security override
                    function_response = get_impact_score(organization.id)
                elif function_name == "get_live_weather":
                    function_response = get_live_weather(function_args.get("city"))
                elif function_name == "predict_food_demand":
                    function_response = predict_food_demand(
                        attendance=function_args.get("attendance"),
                        temperature=function_args.get("temperature", 25.0),
                        rainfall=function_args.get("rainfall", 0.0),
                        holiday=function_args.get("holiday", 0),
                        humidity=function_args.get("humidity", 70.0),
                        exam_day=function_args.get("exam_day", 0),
                        event_flag=function_args.get("event_flag", 0)
                    )
                    
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )
                
            # Send the second request with the tool responses
            second_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
            )
            return second_response.choices[0].message.content.strip()
            
        return response_message.content.strip()
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return "I'm sorry, I encountered an error while trying to find that information for you."
