import copernicusmarine

copernicusmarine.subset(
  dataset_id="METOFFICE-GLO-SST-L4-REP-OBS-SST",
  variables=["analysed_sst"],
  minimum_longitude=38,
  maximum_longitude=39,
  minimum_latitude=17,
  maximum_latitude=18,
  start_datetime="2015-01-21T00:00:00",
  end_datetime="2022-05-31T00:00:00",
)