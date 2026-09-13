FROM mcr.microsoft.com/dotnet/sdk:8.0.303 AS tooling
WORKDIR /source
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
COPY global.json GoalStats.Template.sln ./
COPY .config/ .config/
COPY src/GoalStats.Template.Api/GoalStats.Template.Api.csproj src/GoalStats.Template.Api/
COPY tests/GoalStats.Template.Api.UnitTests/GoalStats.Template.Api.UnitTests.csproj tests/GoalStats.Template.Api.UnitTests/
COPY tests/GoalStats.Template.Api.IntegrationTests/GoalStats.Template.Api.IntegrationTests.csproj tests/GoalStats.Template.Api.IntegrationTests/
RUN dotnet tool restore && dotnet restore GoalStats.Template.sln
COPY src/ src/
COPY tests/ tests/

FROM tooling AS development
ENV ASPNETCORE_HTTP_PORTS=8080 DOTNET_USE_POLLING_FILE_WATCHER=1 DOTNET_WATCH_RESTART_ON_RUDE_EDIT=1
ENV UseArtifactsOutput=true ArtifactsPath=/artifacts
EXPOSE 8080
CMD ["dotnet", "watch", "--non-interactive", "--project", "src/GoalStats.Template.Api", "run", "--no-launch-profile"]

FROM mcr.microsoft.com/dotnet/sdk:8.0.303 AS build
WORKDIR /source
COPY global.json ./
COPY src/GoalStats.Template.Api/GoalStats.Template.Api.csproj src/GoalStats.Template.Api/
RUN dotnet restore src/GoalStats.Template.Api/GoalStats.Template.Api.csproj
COPY src/GoalStats.Template.Api/ src/GoalStats.Template.Api/
RUN dotnet publish src/GoalStats.Template.Api/GoalStats.Template.Api.csproj -c Release --no-restore -o /app/publish /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime
WORKDIR /app
ENV ASPNETCORE_HTTP_PORTS=8080
EXPOSE 8080
USER $APP_UID
COPY --from=build /app/publish .
ENTRYPOINT ["dotnet", "GoalStats.Template.Api.dll"]
