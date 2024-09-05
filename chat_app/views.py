from flask import render_template, request, jsonify
from chat_app import app
import requests
from chat_app.core import SERVER_URL, process_bundle, process_ips, medicationchat
import markdown


print(app.config)


@app.route("/", methods=["GET"])
def hello():
    return render_template("chat.html")


##POST https://fosps.gravitatehealth.eu/focusing/focus/bundlepackageleaflet-es-56a32a5ee239fc834b47c10db1faa3fd?preprocessors=preprocessing-service-manual&patientIdentifier=Cecilia-1&lenses=lens-selector-mvp2_pregnancy


@app.route("/chat/<bundleid>", methods=["POST"])
def lens_app(bundleid=None):
    epibundle = None
    ips = None

    patientIdentifier = request.args.get("patientIdentifier", "")
    model = request.args.get("model", "")
    question = request.args.get("question", "")

    data = request.json
    epibundle = data.get("epi")
    ips = data.get("ips")
    question = data.get("question")

    # print(epibundle)
    if ips is None and patientIdentifier == "":
        return "Error: missing IPS", 404
    # preprocessed_bundle, ips = separate_data(bundleid, patientIdentifier)
    if epibundle is None and bundleid is None:
        return "Error: missing EPI", 404

    if epibundle is None:
        print("epibundle is none")
        # print(epibundle)
        # print(bundleid)
        print(SERVER_URL + "epi/api/fhir/Bundle/" + bundleid)
        epibundle = requests.get(SERVER_URL + "epi/api/fhir/Bundle/" + bundleid).json()
    # print(epibundle)
    language, epi, drug_name = process_bundle(epibundle)
    # GET https://fosps.gravitatehealth.eu/ips/api/fhir/Patient/$summary?identifier=alicia-1

    print(SERVER_URL)
    if ips is None:
        # print(ips)
        ips = requests.get(
            SERVER_URL + "ips/api/fhir/Patient/$summary?identifier=" + patientIdentifier
        ).json()
    # print(ips)
    gender, age, diagnostics, medications = process_ips(ips)

    # Return the JSON response
    chated = medicationchat(
        language,
        drug_name,
        gender,
        age,
        diagnostics,
        medications,
        question,
        epi,
        model="llama3",
    )
    return markdown.markdown(chated["response"])
