# This assumes that the pytest image has already been made
#   as required for the DCTStack/DataServants
FROM pytest

USER lig:lig
WORKDIR /home/lig/Codes/
COPY --chown=lig:lig . ./GOESMcGOESface/
RUN mkdir GOESMcGOESface/outputs GOESMcGOESface/outputs/pngs GOESMcGOESface/outputs/raws GOESMcGOESface/outputs/nows GOESMcGOESface/logs

# Default command to issue when starting this image in a container
USER lig
WORKDIR /home/lig/Codes/GOESMcGOESface/
CMD ["python goes16aws_looper.py"]
