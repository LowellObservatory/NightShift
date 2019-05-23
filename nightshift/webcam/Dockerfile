# This assumes that the pytest image has already been made
#   as required for the DCTStack/DataServants
FROM pytest

USER lig:lig
WORKDIR /home/lig/Codes/
COPY --chown=lig:lig . ./WebcamMcWebcamface/
RUN mkdir WebcamMcWebcamface/images WebcamMcWebcamface/logs

# Default command to issue when starting this image in a container
USER lig
WORKDIR /home/lig/Codes/WebcamMcWebcamface/
CMD ["python camLooper.py"]
