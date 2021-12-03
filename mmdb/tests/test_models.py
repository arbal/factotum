
import pytest
from mmdb.models import MediaSampleSummary

@pytest.mark.django_db
def test_create_mss():
    mss = MediaSampleSummary.objects.create(source_name="USGS Monitoring Data National Water Quality Monitoring Council - Air, Soil, Biological (Tissue), Sediment, Water")
    assert mss.source_name == "USGS Monitoring Data National Water Quality Monitoring Council - Air, Soil, Biological (Tissue), Sediment, Water"
