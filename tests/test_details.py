from proslim_ai.details import _clinical_trials_detail, _parse_pubmed_xml


def test_parse_pubmed_xml_extracts_abstract_and_publication_types():
    xml = """
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>123</PMID>
          <Article>
            <ArticleTitle>Trial title</ArticleTitle>
            <Abstract>
              <AbstractText Label="BACKGROUND">Background text.</AbstractText>
              <AbstractText Label="RESULTS">Results text.</AbstractText>
            </Abstract>
            <PublicationTypeList>
              <PublicationType>Randomized Controlled Trial</PublicationType>
            </PublicationTypeList>
          </Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>
    """

    records = _parse_pubmed_xml(xml)

    assert records["123"]["title"] == "Trial title"
    assert "Background text" in records["123"]["abstract"]
    assert records["123"]["publication_types"] == "Randomized Controlled Trial"


def test_clinical_trials_detail_extracts_interventions_and_outcomes():
    study = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT1", "briefTitle": "Trial"},
            "designModule": {"enrollmentInfo": {"count": 120}, "phases": ["NA"]},
            "armsInterventionsModule": {
                "interventions": [{"name": "Probiotic capsule"}],
                "armGroups": [{"label": "Probiotic"}, {"label": "Placebo"}],
            },
            "outcomesModule": {
                "primaryOutcomes": [{"measure": "Body weight"}],
                "secondaryOutcomes": [{"measure": "Gut microbiota"}],
            },
        }
    }

    detail = _clinical_trials_detail(study)

    assert detail["clinical_interventions"] == "Probiotic capsule"
    assert detail["enrollment"] == "120"
    assert detail["primary_outcomes"] == "Body weight"
    assert detail["arms"] == "Probiotic; Placebo"

