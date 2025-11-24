# Sith Snips

This repository contains code samples for various languages. They may be illustrative, educative, practical, or broken, although the goal is to provide a structured, easy-to-use library of *runnable* code snippets. There is also an `info` folder for helpful technical information that isn't code.

The complete repository name is sql-sith/sith-source-snippets.git. The short name, Sith Snips, is different because they both seem really hard to pronounce, so I want to use them both.

## General Structure

The repository is organized by language at the top level. Each language has its own directory and specific conventions for adding and running snippets.

Here is a sample repo layout.

```
/
├── .gitignore
├── bash/
│   ├── file_management/
│   │   └── create_and_move.sh
│   └── README.md
├── csharp/
│   ├── SimpleHttpServer/
│   │   ├── SimpleHttpServer.csproj
│   │   └── Program.cs
│   └── README.md
├── golang/
│   ├── BasicGoroutines/
│   │   ├── go.mod
│   │   └── main.go
│   └── README.md
├── java/
│   ├── FileIO/
│   │   ├── pom.xml
│   │   └── src/main/java/com/example/FileCopier.java
│   └── README.md
├── nodejs/
│   ├── simple_server/
│   │   ├── index.js
│   │   └── package.json
│   ├── dependency_free/
│   │   └── read_file.js
│   └── README.md
├── powershell/
│   ├── ad_management/
│   │   └── get_ad_users.ps1
│   └── README.md
├── python/
│   ├── data_structures/
│   │   └── binary_tree.py
│   ├── web_scraping/
│   │   ├── scrape_site.py
│   │   └── requirements.txt
│   └── README.md
├── tsql/
│   ├── setup/
│   │   └── create_tables.sql
│   ├── stored_procedures/
│   │   └── get_customer_by_id.sql
│   └── README.md
└── README.md

```

## Language-Specific Instructions

Below are the guidelines for managing snippets in each language directory.

### 🐍 Python (`python/`)

Python is flexible. Most snippets can be self-contained in a single `.py` file.

* **Structure** : Group related scripts into subdirectories (e.g., `web_scraping/`, `data_structures/`).
* **Dependencies** : If a script has dependencies, add a `requirements.txt` file in the same subdirectory.
* **To Add a Snippet** :

1. Create a new subdirectory or choose an existing one.
2. Add your `.py` file.
3. If needed, run `pip freeze > requirements.txt` to capture dependencies.

* **To Run a Snippet** :

```
  # If dependencies exist
  pip install -r python/web_scraping/requirements.txt

  # Run the script
  python python/web_scraping/scrape_site.py

```

### ☕ Java (`java/`)

Java requires a formal project structure for proper compilation and dependency management. We'll use Maven for this.

* **Structure** : Each snippet or small project gets its own directory, which is a self-contained Maven project.
* **To Add a Snippet** :

1. Create a new directory: `java/MyNewSnippet/`.
2. Create a `pom.xml` file inside it to manage dependencies.
3. Create the Java source directory: `mkdir -p java/MyNewSnippet/src/main/java/com/example/`.
4. Add your `.java` file (e.g., `MyNewSnippet.java`) inside the source directory.

* **To Run a Snippet** :

```
  # Navigate to the project directory
  cd java/MyNewSnippet

  # Compile and run using Maven
  mvn compile exec:java -Dexec.mainClass="com.example.MyNewSnippet"

```

### 🐹 Go (`golang/`)

Go works best with modules, which helps manage dependencies and project structure.

* **Structure** : Each snippet should be its own Go module in a separate directory.
* **To Add a Snippet** :

1. Create a new directory: `golang/MyGoSnippet/`.
2. Navigate into it: `cd golang/MyGoSnippet/`.
3. Initialize a Go module: `go mod init example.com/mygosnippet`.
4. Create your `main.go` file inside.

* **To Run a Snippet** :

```
  # Navigate to the snippet's directory
  cd golang/MyGoSnippet

  # Run the code
  go run .

```

### C# (`csharp/`)

C# snippets are best managed as individual .NET console projects.

* **Structure** : Each snippet resides in its own directory, initialized as a .NET project.
* **To Add a Snippet** :

1. Create a new directory: `csharp/MyCSharpSnippet/`.
2. Navigate into it: `cd csharp/MyCSharpSnippet/`.
3. Create a new console application: `dotnet new console`.
4. This creates the `.csproj` file and a `Program.cs`. Edit `Program.cs` with your snippet code.
5. To add dependencies, use `dotnet add package <PackageName>`.

* **To Run a Snippet** :

```
  # Navigate to the project directory
  cd csharp/MyCSharpSnippet

  # Run the application
  dotnet run

```

### 🟩 Node.js (`nodejs/`)

Node.js snippets can be single files, but anything with dependencies should have its own `package.json`.

* **Structure** :
* For dependency-free snippets, you can place the `.js` file in a generic folder like `dependency_free/`.
* For snippets with dependencies, create a dedicated subdirectory.
* **To Add a Snippet (with dependencies)** :

1. Create a new directory: `nodejs/MyNodeSnippet/`.
2. Navigate into it: `cd nodejs/MyNodeSnippet/`.
3. Initialize a project: `npm init -y`.
4. Install dependencies: `npm install <package-name>`.
5. Add your `index.js` file.

* **To Run a Snippet** :

```
  # For a snippet with dependencies
  cd nodejs/MyNodeSnippet
  npm install
  node index.js

  # For a dependency-free snippet
  node nodejs/dependency_free/read_file.js

```

### 📜 Bash (`bash/`) & PowerShell (`powershell/`)

These scripting languages are straightforward.

* **Structure** : Store scripts in `.sh` (Bash) or `.ps1` (PowerShell) files. Organize them into subdirectories by topic (e.g., `file_management/`).
* **To Run a Snippet** :

```
  # Make Bash script executable (optional, but good practice)
  chmod +x bash/file_management/create_and_move.sh

  # Run Bash script
  ./bash/file_management/create_and_move.sh

  # Run PowerShell script
  pwsh powershell/ad_management/get_ad_users.ps1

```

### 🗄️ Transact-SQL (`tsql/`)

SQL scripts aren't "run" directly but are executed against a database. The key is providing context.

* **Structure** :
* Organize `.sql` files by function (e.g., `stored_procedures/`, `views/`, `data_manipulation/`).
* Include a `setup/` directory with scripts to create necessary tables and data for testing the snippets.
* **Usage** : Each `.sql` file should contain comments explaining its purpose, parameters, and the database context it expects to run in. Users will copy and execute these scripts in a SQL client like SSMS or Azure Data Studio.

