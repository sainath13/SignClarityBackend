import time

from sanic import Sanic, response
from sanic.response import text
from gradio_client import Client
# import cohere
import re
import json
from sanic_cors import CORS, cross_origin
from dropbox_sign import \
    ApiClient, ApiException, Configuration, apis

app = Sanic("HelloClarityServer")
CORS(app)
configuration = Configuration(
    username="ce0fbce605d1f3121a0e90ae3616a9af99a771f260376d2215a478cff05dfa51",
)

pdf_client = Client("https://haouarin-pdftotext.hf.space/")
llamav2_client = Client("https://ysharma-explore-llamav2-with-tgi.hf.space/")


# co = cohere.Client('vmQf5O1lssh1nDhgfZvanDllOlrN5GCmCshivIIX')


@app.get("/")
async def hello_world(request):
    return text("Hello, world.")


@app.route("/context", methods=['POST'])
async def get_context(request):
    input_data = json.loads(request.body)
    description = input_data['description']
    prompt_text = "Simplify text : " + description
    # time.sleep(1)
    answer = llamav2_client.predict(
        prompt_text,  # str in 'Message' Textbox component
        "Use Simple language that a common man can understand",  # str in 'Optional system prompt' Textbox component
        0.9,  # Temperature ( numeric value between 0.0 and 1.0)
        512,  # Max new tokens (numeric value between 0 and 4096)
        0.4,  # Top-p (nucleus sampling) (numeric value between 0.0 and 1)
        1.2,  # Repetition penalty(numeric value between 1.0 and 2.0)
        api_name="/chat"
    )
    #replace the ending char sequence for llamav2 chat model
    answer = answer.replace("</s>", "")
    answer = "Simply means: " + answer
    return response.json({
        "code": "200",
        "summary": answer,
        "originalData": description,
        "reason": "Success"
    })


def get_pdf_text():
    result = pdf_client.predict(
        ["file_response.pdf"],
        api_name="/predict"
    )
    return result


@app.route("/chat", methods=['POST'])
async def get_chat_response(request):
    data = json.loads(request.body)
    question = data['question']
    information = data['information']
    prompt_text = "Using following text : " + information + ", Please answer the question : " + question
    answer = llamav2_client.predict(
        prompt_text,  # str in 'Message' Textbox component
        "Use Simple language that a common man can understand",  # str in 'Optional system prompt' Textbox component
        0.9,  # Temperature ( numeric value between 0.0 and 1.0)
        1024,  # Max new tokens (numeric value between 0 and 4096)
        0.4,  # Top-p (nucleus sampling) (numeric value between 0.0 and 1)
        1.2,  # Repetition penalty(numeric value between 1.0 and 2.0)
        api_name="/chat"
    )

    #replace the ending char sequence for llamav2 chat model
    answer = answer.replace("</s>", "")
    return response.json({
        "code": "200",
        "answer": answer,
        "reason": "Success"
    })


def get_summary_and_title_description(pdf_text):
    result = []
    index_pattern = r"\n\d+[\.\)\\n]"
    index_matches = re.finditer(index_pattern, pdf_text)
    index_positions = [match.start() for match in index_matches]
    extracted_texts = []
    start_index = 0
    end_index = 0
    for i in range(len(index_positions)):
        if (i < len(index_positions) - 1):
            start_index = index_positions[i] + 3
            end_index = index_positions[i + 1]
        else:
            end_of_input = "\n\n"
            prev_end_index = end_index
            end_index = pdf_text[prev_end_index:].find(end_of_input)
            end_index = end_index + prev_end_index
            start_index = index_positions[i] + 3

        # Extract text between the start and end indices
        extracted_text = pdf_text[start_index:end_index].strip()
        extracted_texts.append(extracted_text)

    # Print the extracted texts
    for i, extracted_text in enumerate(extracted_texts, 1):
        extracted_text = extracted_text.replace("\n", " ")
        # print(f"Extracted Text {i}:\n{extracted_text}\n")
        pattern = r"^(.*?)[.:](.*)$"
        match = re.match(pattern, extracted_text)
        if match:
            title = match.group(1)
            detail = match.group(2)
            temp_result = {"title": title.strip(), "detail": detail.strip()}
            print(temp_result)
            result.append(temp_result)
        else:
            print("No match found")

    summary_result = llamav2_client.predict(
        pdf_text,  # str in 'Message' Textbox component
        "Use Simple language that a common man can understand. ignore hardcoded details for input fields. Please "
        "summarize, simplify, and contextualize the provided text. Directly start with the summary output. dont start "
        "with any message. Just start with the summary output.",  # str in 'Optional system prompt' Textbox component
        0.9,  # Temperature ( numeric value between 0.0 and 1.0)
        2048,  # Max new tokens (numeric value between 0 and 4096)
        0.4,  # Top-p (nucleus sampling) (numeric value between 0.0 and 1)
        1.2,  # Repetition penalty(numeric value between 1.0 and 2.0)
        api_name="/chat"
    )

    summary_title_description_result = {'summary': summary_result, 'originalTexts': result}
    return summary_title_description_result


@app.get("/summary/<signid>")
async def get_summary(request, signid):
    with ApiClient(configuration) as api_client:
        signature_request_api = apis.SignatureRequestApi(api_client)
        signature_request_id = signid
        try:
            dropbox_response = signature_request_api.signature_request_files(signature_request_id, file_type="pdf")
            open('file_response.pdf', 'wb').write(dropbox_response.read())
            print("Success")
        except ApiException as e:
            print("Exception when calling Dropbox Sign API: %s\n" % e)
    pdf_text = get_pdf_text()

    result = get_summary_and_title_description(pdf_text)
    return response.json({
        "code": "200",
        "summary": result['summary'],
        "originalTexts": result['originalTexts'],
        "reason": "Success"
    })


@app.get("/default/<signid>")
async def get_default(request, signid):
    output = """
    ---
file name: /tmp/gradio/83a4951112c9d7600803584abf1e8877fc6269ec/file_response.pdf
 content: 
Mutual Non-Disclosure Agreement 
 
This Nondisclosure Agreement (the "Agreement") is entered into by and between ABC Company 
with its principal offices at 123 Alphabet Street, San Francisco, CA 94101, ("Disclosing Party") 
and _________________________________________, located at 
__________________________________ ("Receiving Party") for the purpose of preventing the 
unauthorized disclosure of Confidential Information as defined below. The parties agree to enter 
into a confidential relationship with respect to the disclosure of certain proprietary and confidential 
information ("Confidential Information"). 
 
1.   Definition of Confidential Information. For purposes of this Agreement, "Confidential 
Information" shall include all information or material that has or could have commercial value or 
other utility in the business in which Disclosing Party is engaged. If Confidential Information is in 
written form, the Disclosing Party shall label or stamp the materials with the word "Confidential" or 
some similar warning. If Confidential Information is transmitted orally, the Disclosing Party shall 
promptly provide a writing indicating that such oral communication constituted Confidential 
Information. 

2.   Exclusions from Confidential Information. Receiving Party's obligations under this Agreement
do not extend to information that is: (a) publicly known at the time of disclosure or subsequently
becomes publicly known through no fault of the Receiving Party; (b) discovered or created by the 
Receiving Party before disclosure by Disclosing Party; (c) learned by the Receiving Party through 
legitimate means other than from the Disclosing Party or Disclosing Party's representatives; or (d) 
is disclosed by Receiving Party with Disclosing Party's prior written approval. 
 
3.   Obligations of Receiving Party. Receiving Party shall hold and maintain the Confidential 
Information in strictest confidence for the sole and exclusive benefit of the Disclosing Party. 
Receiving Party shall carefully restrict access to Confidential Information to employees, 
contractors and third parties as is reasonably required and shall require those persons to sign 
nondisclosure restrictions at least as protective as those in this Agreement. Receiving Party shall 
not, without prior written approval of Disclosing Party, use for Receiving Party's own benefit, 
publish, copy, or otherwise disclose to others, or permit the use by others for their benefit or to 
the detriment of Disclosing Party, any Confidential Information. Receiving Party shall return to 
Disclosing Party any and all records, notes, and other written, printed, or tangible materials in its 
possession pertaining to Confidential Information immediately if Disclosing Party requests it in 
writing. 
 
4.   Time Periods. The nondisclosure provisions of this Agreement shall survive the termination of 
this Agreement and Receiving Party's duty to hold Confidential Information in confidence shall 
remain in effect until the Confidential Information no longer qualifies as a trade secret or until Disclosing Party sends Receiving Party written notice releasing Receiving Party from this 
Agreement, whichever occurs first. 
 
5.   Relationships. Nothing contained in this Agreement shall be deemed to constitute either party 
a partner, joint venturer or employee of the other party for any purpose. 
 
6.   Severability. If a court finds any provision of this Agreement invalid or unenforceable, the 
remainder of this Agreement shall be interpreted so as best to effect the intent of the parties. 
 
7.   Integration. This Agreement expresses the complete understanding of the parties with respect 
to the subject matter and supersedes all prior proposals, agreements, representations and 
understandings. This Agreement may not be amended except in a writing signed by both parties. 
 
8.   Waiver. The failure to exercise any right provided in this Agreement shall not be a waiver of 
prior or subsequent rights. 
 
9.   Notice of Immunity  
Employee is provided notice that an individual shall not be held criminally or civilly liable under any 
federal or state trade secret law for the disclosure of a trade secret that is made (i) in confidence 
to a federal, state, or local government official, either directly or indirectly, or to an attorney; and (ii) 
solely for the purpose of reporting or investigating a suspected violation of law; or is made in a 
complaint or other document filed in a lawsuit or other proceeding, if such filing is made under 
seal. An individual who files a lawsuit for retaliation by an employer for reporting a suspected 
violation of law may disclose the trade secret to the attorney of the individual and use the trade 
secret information in the court proceeding, if the individual (i) files any document containing the 
trade secret under seal; and (ii) does not disclose the trade secret, except pursuant to court 
order. 
 
This Agreement and each party's obligations shall be binding on the representatives, assigns and 
successors of such party. Each party has signed this Agreement through its authorized 
representative. 
 
Company 
 
Signature: _________________________ 
 
 
Name: ____________________________ 
 
 
Date: _____________________________ Recipient 
 
Signature: _________________________ 
 
 
Name: ____________________________ 
 
 
Date: _____________________________ 
 NDA with Acme Co.
0a9ad55670de6a3efc65d855ac9ed885b5198997
Sainath
User ID: 39313138313035383534
---

    """

    summary = """A mutual non-disclosure agreement is a legal contract that is signed by two parties who wish to 
    share confidential information with each other, but wish to ensure that the information remains secret. The 
    agreement outlines the terms under which the information can be shared, and what measures must be taken to ensure 
    that the information remains confidential."""
    summary = """Summary:\n\nThe Mutual Non-Disclosure Agreement (NDA) outlines the terms of confidentiality between two parties, ABC Company and the recipient, regarding the exchange of sensitive information. Both parties agree to keep shared information strictly confidential and prohibit its unauthorized disclosure. The agreement defines what constitutes Confidential Information and excludes information that is already public knowledge or obtained through legitimate means. The receiving party must limit access to Confidential Information and obtain permission before using or disclosing it. The agreement remains effective until the information no longer qualifies as a trade secret or until one party releases the other from the agreement. It also states that nothing in the agreement implies a partnership or employment relationship between the parties. In case of any dispute, the validity of the remaining agreement will not be affected, and the parties will resolve disputes through arbitration. Finally, the agreement includes a notice of immunity for individuals who report suspected legal violations.</s>"""
    originalTexts = []
    zero = {"title": "Definition of Confidential Information.",
            "detail": """For purposes of this Agreement, "Confidential 
Information" shall include all information or material that has or could have commercial value or 
other utility in the business in which Disclosing Party is engaged. If Confidential Information is in 
written form, the Disclosing Party shall label or stamp the materials with the word "Confidential" or 
some similar warning. If Confidential Information is transmitted orally, the Disclosing Party shall 
promptly provide a writing indicating that such oral communication constituted Confidential 
Information. """
            }
    one = {"title": "Exclusions from Confidential Information",
           "detail": """Receiving Party's obligations under this Agreement 
do not extend to information that is: (a) publicly known at the time of disclosure or subsequently 
becomes publicly known through no fault of the Receiving Party; (b) discovered or created by the 
Receiving Party before disclosure by Disclosing Party; (c) learned by the Receiving Party through 
legitimate means other than from the Disclosing Party or Disclosing Party's representatives; or (d) 
is disclosed by Receiving Party with Disclosing Party's prior written approval. """
           }
    two = {"title": "Obligations of Receiving Party",
           "detail": """Receiving Party shall hold and maintain the Confidential 
Information in strictest confidence for the sole and exclusive benefit of the Disclosing Party. 
Receiving Party shall carefully restrict access to Confidential Information to employees, 
contractors and third parties as is reasonably required and shall require those persons to sign 
nondisclosure restrictions at least as protective as those in this Agreement. Receiving Party shall 
not, without prior written approval of Disclosing Party, use for Receiving Party's own benefit, 
publish, copy, or otherwise disclose to others, or permit the use by others for their benefit or to 
the detriment of Disclosing Party, any Confidential Information. Receiving Party shall return to 
Disclosing Party any and all records, notes, and other written, printed, or tangible materials in its 
possession pertaining to Confidential Information immediately if Disclosing Party requests it in 
writing."""
           }
    three = {"title": "Time Periods",
             "detail": """The nondisclosure provisions of this Agreement shall survive the termination of 
this Agreement and Receiving Party's duty to hold Confidential Information in confidence shall 
remain in effect until the Confidential Information no longer qualifies as a trade secret or until Disclosing Party sends Receiving Party written notice releasing Receiving Party from this 
Agreement, whichever occurs first. """
             }
    four = {"title": "Relationships",
            "detail": """ Nothing contained in this Agreement shall be deemed to constitute either party 
a partner, joint venturer or employee of the other party for any purpose. """
            }
    five = {"title": "Severability",
            "detail": """If a court finds any provision of this Agreement invalid or unenforceable, the 
remainder of this Agreement shall be interpreted so as best to effect the intent of the parties. """
            }
    six = {"title": "Integration",
           "detail": """This Agreement expresses the complete understanding of the parties with respect 
to the subject matter and supersedes all prior proposals, agreements, representations and 
understandings. This Agreement may not be amended except in a writing signed by both parties. """
           }
    seven = {"title": "Waiver",
             "detail": """The failure to exercise any right provided in this Agreement shall not be a waiver of 
prior or subsequent rights. """
             }
    eight = {"title": "Notice of Immunity  ",
             "detail": """Employee is provided notice that an individual shall not be held criminally or civilly liable under any 
federal or state trade secret law for the disclosure of a trade secret that is made (i) in confidence 
to a federal, state, or local government official, either directly or indirectly, or to an attorney; and (ii) 
solely for the purpose of reporting or investigating a suspected violation of law; or is made in a 
complaint or other document filed in a lawsuit or other proceeding, if such filing is made under 
seal. An individual who files a lawsuit for retaliation by an employer for reporting a suspected 
violation of law may disclose the trade secret to the attorney of the individual and use the trade 
secret information in the court proceeding, if the individual (i) files any document containing the 
trade secret under seal; and (ii) does not disclose the trade secret, except pursuant to court 
order. """
             }
    originalTexts.append(zero)
    originalTexts.append(one)
    originalTexts.append(two)
    originalTexts.append(three)
    originalTexts.append(four)
    originalTexts.append(five)
    originalTexts.append(six)
    originalTexts.append(seven)
    originalTexts.append(eight)
    time.sleep(1)
    return response.json({
        "code": "200",
        "summary": summary,
        "originalTexts": originalTexts,
        "reason": "Success"
    })


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)
