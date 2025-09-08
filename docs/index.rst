.. DAGLab documentation master file

Welcome to DAGLab's documentation!
==================================

DAGLab is a powerful Python library for building, executing, and analyzing computational DAGs with ML inference capabilities.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   introduction
   quickstart
   api/index
   examples/index
   tutorials/index

Key Features
------------

* **Intuitive API**: Build complex computational graphs with simple Python code
* **Multiple Compute Backends**: Local, Ray, Dask, and Spark support
* **ML Integration**: Seamless integration with PyTorch, TensorFlow, and ONNX
* **Rich Visualizations**: Interactive DAG visualization with multiple backends
* **Production Ready**: Built-in monitoring, logging, and error handling
* **Extensible**: Plugin architecture for custom nodes and backends

Installation
------------

Install DAGLab using pip:

.. code-block:: bash

   pip install daglab

For development:

.. code-block:: bash

   pip install daglab[dev]

Quick Example
-------------

.. code-block:: python

   from daglab import DAG, Node, Edge
   from daglab.compute import LocalCompute
   
   # Create a DAG
   dag = DAG(name="my_pipeline")
   
   # Add nodes
   dag.add_node(Node(id="input", function=lambda: {"data": [1, 2, 3]}))
   dag.add_node(Node(id="process", function=lambda x: {"result": sum(x["data"])}))
   
   # Connect nodes
   dag.add_edge(Edge(source="input", target="process"))
   
   # Execute
   compute = LocalCompute()
   result = compute.execute(dag)

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`