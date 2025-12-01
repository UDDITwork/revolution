# SPDX-FileCopyrightText: Copyright (c) 2023-2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import base64
import streamlit as st
import fitz
from io import BytesIO
from PIL import Image
import requests

def get_b64_image_from_content(image_content):
    """Convert image content to base64 encoded string."""
    img = Image.open(BytesIO(image_content))
    if img.mode != 'RGB':
        img = img.convert('RGB')
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def is_graph(image_content):
    """Determine if an image is a graph, plot, chart, or table."""
    res = describe_image(image_content)
    return any(keyword in res.lower() for keyword in ["graph", "plot", "chart", "table"])

def process_graph(image_content, llm):
    """Process a graph image and generate a description."""
    deplot_description = process_graph_deplot(image_content)
    response = llm.complete("Your responsibility is to explain charts. You are an expert in describing the responses of linearized tables into plain English text for LLMs to use. Explain the following linearized table. " + deplot_description)
    return response.text

def describe_image(image_content):
    """Generate a description of an image using Claude's Vision API."""
    import anthropic

    image_b64 = get_b64_image_from_content(image_content)
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise ValueError("ANTHROPIC API Key is not set. Please set the ANTHROPIC_API_KEY environment variable.")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": """Analyze this presentation slide image and provide a detailed description covering:

1. **Text Content**: All visible text, headings, titles, and labels
2. **Visual Elements**: Diagrams, flowcharts, charts, graphs, tables, or illustrations
3. **Structure**: How information is organized (boxes, arrows, connections, hierarchy)
4. **Key Concepts**: Main ideas, processes, or workflows shown
5. **Technical Details**: Any code, formulas, architecture patterns, or implementation details

Be specific about flowcharts, diagrams, and architectural elements. Mention any numbered items (like "Implement 1", "Implement 2", etc.) or section labels."""
                    }
                ],
            }
        ],
    )

    return message.content[0].text

def process_graph_deplot(image_content):
    """Process a graph image using NVIDIA's Deplot API."""
    invoke_url = "https://ai.api.nvidia.com/v1/vlm/google/deplot"
    image_b64 = get_b64_image_from_content(image_content)
    api_key = os.getenv("NVIDIA_API_KEY")
    
    if not api_key:
        raise ValueError("NVIDIA API Key is not set. Please set the NVIDIA_API_KEY environment variable.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }

    payload = {
        "messages": [
            {
                "role": "user",
                "content": f'Generate underlying data table of the figure below: <img src="data:image/png;base64,{image_b64}" />'
            }
        ],
        "max_tokens": 1024,
        "temperature": 0.20,
        "top_p": 0.20,
        "stream": False
    }

    response = requests.post(invoke_url, headers=headers, json=payload)
    response_data = response.json()

    # Debug: print the actual response to understand the format
    print(f"DePlot API response: {response_data}")

    # Check if the response has an error
    if "error" in response_data:
        print(f"DePlot API error: {response_data['error']}")
        raise ValueError(f"DePlot API error: {response_data.get('error', {}).get('message', 'Unknown error')}")

    # Try to extract the content
    if "choices" in response_data:
        return response_data["choices"][0]['message']['content']
    else:
        raise KeyError(f"Unexpected response format from DePlot API. Response keys: {response_data.keys()}")

def extract_text_around_item(text_blocks, bbox, page_height, threshold_percentage=0.1):
    """Extract text above and below a given bounding box on a page."""
    before_text, after_text = "", ""
    vertical_threshold_distance = page_height * threshold_percentage
    horizontal_threshold_distance = bbox.width * threshold_percentage

    for block in text_blocks:
        block_bbox = fitz.Rect(block[:4])
        vertical_distance = min(abs(block_bbox.y1 - bbox.y0), abs(block_bbox.y0 - bbox.y1))
        horizontal_overlap = max(0, min(block_bbox.x1, bbox.x1) - max(block_bbox.x0, bbox.x0))

        if vertical_distance <= vertical_threshold_distance and horizontal_overlap >= -horizontal_threshold_distance:
            if block_bbox.y1 < bbox.y0 and not before_text:
                before_text = block[4]
            elif block_bbox.y0 > bbox.y1 and not after_text:
                after_text = block[4]
                break

    return before_text, after_text

def process_text_blocks(text_blocks, char_count_threshold=500):
    """Group text blocks based on a character count threshold."""
    current_group = []
    grouped_blocks = []
    current_char_count = 0

    for block in text_blocks:
        if block[-1] == 0:  # Check if the block is of text type
            block_text = block[4]
            block_char_count = len(block_text)

            if current_char_count + block_char_count <= char_count_threshold:
                current_group.append(block)
                current_char_count += block_char_count
            else:
                if current_group:
                    grouped_content = "\n".join([b[4] for b in current_group])
                    grouped_blocks.append((current_group[0], grouped_content))
                current_group = [block]
                current_char_count = block_char_count

    # Append the last group
    if current_group:
        grouped_content = "\n".join([b[4] for b in current_group])
        grouped_blocks.append((current_group[0], grouped_content))

    return grouped_blocks

def save_uploaded_file(uploaded_file):
    """Save an uploaded file to a temporary directory."""
    temp_dir = os.path.join(os.getcwd(), "vectorstore", "ppt_references", "tmp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, uploaded_file.name)
    
    with open(temp_file_path, "wb") as temp_file:
        temp_file.write(uploaded_file.read())
    
    return temp_file_path