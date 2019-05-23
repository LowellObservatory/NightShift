# This assumes that the pytest image has already been made
#   as required for the DCTStack/DataServants
FROM pytest

# Not every image needs this, so we'll do it as a one-off in here
USER root:root
RUN conda install -y -c conda-forge arm_pyart

USER lig:lig
WORKDIR /home/lig/Codes/
COPY --chown=lig:lig . ./RadarLove/
RUN mkdir RadarLove/outputs RadarLove/outputs/pngs RadarLove/outputs/raws RadarLove/outputs/nows RadarLove/logs

# Default command to issue when starting this image in a container
USER lig
WORKDIR /home/lig/Codes/RadarLove/
CMD ["python nexradaws_looper.py"]
