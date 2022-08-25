A script that can be used to automate blind sql injection.

To use, replace the inject function with a function that returns True in the case of a success condition and then run:

blindmysql.py (to get the database version)

blindmysql.py &lt;dbms&gt; (to get the databases)

blindmysql.py &lt;dbms&gt; &lt;database&gt; (to get tables for a given database)

blindmysql.py &lt;dbms&gt; &lt;database&gt; &lt;table&gt; (to get columns for a given table)

blindmysql.py &lt;dbms&gt; &lt;database&gt; &lt;table&gt; &lt;comma separated columns&gt; (to dump the data in the given columns within the given table)

blindmysql.py --interactive (Execute custom queries against the database)