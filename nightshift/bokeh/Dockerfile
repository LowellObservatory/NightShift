# This assumes that the pytest image has already been made
#   as required for the DCTStack/DataServants
FROM pytest

USER root:root
RUN pip install bokeh

USER lig:lig
WORKDIR /home/lig/Codes/
COPY --chown=lig:lig . ./BokehMcBokehface/
RUN mkdir BokehMcBokehface/logs

# Default command to issue when starting this image in a container
USER lig
WORKDIR /home/lig/Codes/BokehMcBokehface/
CMD ["python serve.py"]
