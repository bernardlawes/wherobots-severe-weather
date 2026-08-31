from wherobots import WherobotsJob

job = WherobotsJob(
    script="s3://wbts-wbc-u6dmun8w17/htgag89foc/data/customer-fnd4dluzk4dpqg/wherobots_weather_exposure_job.py",
    name="severe-weather-east-coast-15region-2026",
    runtime="small",
    timeout_seconds=3600,
    args=["--regions", "US-ME,US-NH,US-MA,US-RI,US-CT,US-NY,US-NJ,US-DE,US-MD,US-DC,US-VA,US-NC,US-SC,US-GA,US-FL"],
)

print("Submitting Wherobots job...")
job.submit()

print("Job submitted.")

status = job.wait_for_completion(stream_logs=True)
print(f"Finished with status: {status.value}")